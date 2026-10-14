import contextlib
import os
import time
import xml.etree.ElementTree as ET

import libvirt

from isolagent.session import SessionError


def get_libvirt_connection(profile=None):
    """
    Opens connection to libvirt using configurable URI.

    Priority: ISOLAGENT_LIBVIRT_URI env var > profile runtime.libvirt_uri > qemu:///system
    """
    uri = os.environ.get("ISOLAGENT_LIBVIRT_URI")
    if not uri and profile:
        uri = profile.get("runtime", {}).get("libvirt_uri")
    if not uri:
        uri = "qemu:///system"

    try:
        conn = libvirt.open(uri)
        return conn
    except libvirt.libvirtError as e:
        raise SessionError(
            f"Failed to connect to libvirt at {uri}: {e}\n"
            "Ensure libvirtd is running and you have appropriate access.\n"
            "For system-level access, you may need to add your user to the 'libvirt' group."
        ) from e


def get_default_pool(conn):
    """Look up the pool named 'default'. Raise SessionError if not found or not active."""
    try:
        pool = conn.storagePoolLookupByName("default")
    except libvirt.libvirtError as e:
        raise SessionError(
            "libvirt storage pool 'default' not found — create it with:\n"
            "  virsh pool-define-as default dir --target /var/lib/libvirt/images"
            " && virsh pool-start default && virsh pool-autostart default"
        ) from e

    if not pool.isActive():
        raise SessionError(
            "libvirt storage pool 'default' is not active — run: virsh pool-start default"
        )

    return pool


def volume_exists(conn, name):
    """Check if a volume with the given name exists in the default pool."""
    pool = get_default_pool(conn)
    try:
        pool.storageVolLookupByName(name)
        return True
    except libvirt.libvirtError:
        return False


def get_volume_path(conn, name):
    """Get the filesystem path of a named volume. Raise SessionError if not found."""
    pool = get_default_pool(conn)
    try:
        vol = pool.storageVolLookupByName(name)
        return vol.path()
    except libvirt.libvirtError as e:
        raise SessionError(f"Volume '{name}' not found in default storage pool") from e


def upload_volume(conn, name, local_path, capacity_bytes):
    """
    Upload a local file as a new volume in the default pool.

    If a volume with that name already exists, delete it first.
    """
    pool = get_default_pool(conn)

    if volume_exists(conn, name):
        vol = pool.storageVolLookupByName(name)
        vol.delete(0)

    vol_xml = f"""
<volume>
  <name>{name}</name>
  <capacity unit='bytes'>{capacity_bytes}</capacity>
  <target>
    <format type='qcow2'/>
  </target>
</volume>
"""

    vol = pool.createXML(vol_xml, 0)

    stream = conn.newStream(0)
    vol.upload(stream, 0, capacity_bytes, 0)

    with open(local_path, "rb") as f:

        def send_data(stream, nbytes, opaque):
            data = f.read(nbytes)
            return data

        stream.sendAll(send_data, None)

    stream.finish()


def create_overlay_volume(conn, name, backing_vol_name, capacity_bytes):
    """
    Create a new qcow2 volume backed by another volume.

    The overlay's virtual capacity is set to capacity_bytes.
    """
    pool = get_default_pool(conn)
    backing_path = get_volume_path(conn, backing_vol_name)

    vol_xml = f"""
<volume>
  <name>{name}</name>
  <capacity unit='bytes'>{capacity_bytes}</capacity>
  <target>
    <format type='qcow2'/>
  </target>
  <backingStore>
    <path>{backing_path}</path>
    <format type='qcow2'/>
  </backingStore>
</volume>
"""

    pool.createXML(vol_xml, 0)


def delete_volume(conn, name):
    """Delete a volume by name. Suppress errors if volume doesn't exist."""
    try:
        pool = get_default_pool(conn)
        vol = pool.storageVolLookupByName(name)
        vol.delete(0)
    except libvirt.libvirtError:
        pass


def get_volume_virtual_size(conn, name):
    """
    Get a volume's real virtual size in bytes.

    Refreshes the storage pool first so libvirt re-probes volume backing
    files — the declared capacity of uploaded volumes reflects the allocated
    file size, not the qcow2 virtual disk size. Reads capacity from the
    volume XML because vol.info() is unreliable in some libvirt Python
    bindings (no virStorageVol.refresh, malformed info() tuples). Raises
    SessionError if probing fails or the reported capacity is zero.
    """
    pool = get_default_pool(conn)
    try:
        pool.refresh(0)
        vol = pool.storageVolLookupByName(name)
        vol_xml = ET.fromstring(vol.XMLDesc(0))
        capacity_elem = vol_xml.find("capacity")
        capacity = int(capacity_elem.text) if capacity_elem is not None else 0
    except (libvirt.libvirtError, ValueError, ET.ParseError) as e:
        raise SessionError(f"Could not determine virtual size of volume '{name}': {e}") from e

    if not capacity:
        raise SessionError(
            f"Volume '{name}' reports zero virtual size — the backing image "
            "may be corrupt or unreadable"
        )

    return capacity


def check_default_network(conn):
    """
    Verify the 'default' network is active.

    Raises SessionError if not defined or not active.
    """
    try:
        network = conn.networkLookupByName("default")
    except libvirt.libvirtError as e:
        raise SessionError(
            "libvirt default network not found — ensure libvirt is properly installed"
        ) from e

    if not network.isActive():
        raise SessionError("libvirt default network is not active — run: virsh net-start default")


_SIZE_UNITS = {"M": "MiB", "G": "GiB", "T": "TiB"}
_UNIT_BYTES = {"MiB": 1024**2, "GiB": 1024**3, "TiB": 1024**4}


def parse_size(size_str):
    """Parse size string like '4G', '512M' or '1T' to (value, unit) for libvirt XML."""
    normalized = size_str.strip().upper()

    if len(normalized) >= 2 and normalized[-1] in _SIZE_UNITS:
        value_part = normalized[:-1]
        if value_part.isdigit():
            return int(value_part), _SIZE_UNITS[normalized[-1]]

    raise ValueError(f"Invalid size format: {size_str}")


def parse_size_bytes(size_str):
    """Parse size string like '20G' to an integer number of bytes."""
    value, unit = parse_size(size_str)
    return value * _UNIT_BYTES[unit]


def generate_domain_xml(
    name, memory, cpus, disk_path, cloud_init_iso_path, console_log_path, profile_name
):
    """
    Returns a valid libvirt domain XML string.

    Includes: q35 machine, KVM, virtio disk + sata cdrom, virtio-net on default network,
    vhost-vsock with auto CID, serial console, and profile metadata.
    """
    mem_value, mem_unit = parse_size(memory)

    xml = f"""
<domain type='kvm'>
  <name>{name}</name>
  <metadata>
    <isolagent:profile xmlns:isolagent="http://isolagent.local/">{profile_name}</isolagent:profile>
  </metadata>
  <memory unit='{mem_unit}'>{mem_value}</memory>
  <currentMemory unit='{mem_unit}'>{mem_value}</currentMemory>
  <vcpu placement='static'>{cpus}</vcpu>
  <os>
    <type arch='x86_64' machine='q35'>hvm</type>
  </os>
  <features>
    <acpi/>
    <apic/>
  </features>
  <cpu mode='host-passthrough'/>
  <clock offset='utc'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>destroy</on_reboot>
  <on_crash>destroy</on_crash>
  <devices>
    <emulator>/usr/bin/qemu-system-x86_64</emulator>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file='{disk_path}'/>
      <target dev='vda' bus='virtio'/>
    </disk>
    <disk type='file' device='cdrom'>
      <driver name='qemu' type='raw'/>
      <source file='{cloud_init_iso_path}'/>
      <target dev='sda' bus='sata'/>
      <readonly/>
    </disk>
    <interface type='network'>
      <source network='default'/>
      <model type='virtio'/>
    </interface>
    <vsock model='virtio'>
      <cid auto='yes'/>
    </vsock>
    <serial type='file'>
      <source path='{console_log_path}'/>
      <target type='isa-serial' port='0'>
        <model name='isa-serial'/>
      </target>
    </serial>
    <console type='file'>
      <source path='{console_log_path}'/>
      <target type='serial' port='0'/>
    </console>
  </devices>
</domain>
""".strip()

    return xml


def generate_domain_name(profile_name):
    """
    Returns isolagent-{profile_name}-{suffix} where suffix is 6 hex chars.

    Validates that profile_name contains only alphanumeric, hyphen, underscore.
    """
    import re

    if not re.match(r"^[a-zA-Z0-9_-]+$", profile_name):
        raise ValueError(
            f"Invalid profile name '{profile_name}': "
            "only alphanumeric, hyphen, and underscore allowed"
        )

    suffix = os.urandom(3).hex()
    return f"isolagent-{profile_name}-{suffix}"


def discover_guest_ip(domain, conn):
    """
    Discover the guest's IPv4 address.

    Primary: poll domain.interfaceAddresses()
    Fallback: read MAC from domain XML, poll network.DHCPLeases()
    Retry for up to 30 seconds.
    """
    deadline = time.time() + 30

    while time.time() < deadline:
        try:
            ifaces = domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE)

            for _iface_name, iface_data in ifaces.items():
                if not iface_data or "addrs" not in iface_data:
                    continue

                for addr in iface_data["addrs"]:
                    if addr["type"] == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                        ip = addr["addr"]
                        if not ip.startswith("127."):
                            return ip
        except libvirt.libvirtError:
            pass

        try:
            xml_str = domain.XMLDesc(0)
            root = ET.fromstring(xml_str)

            mac_elem = root.find(".//interface[@type='network']/mac")
            if mac_elem is not None:
                mac = mac_elem.get("address")

                network = conn.networkLookupByName("default")
                leases = network.DHCPLeases(mac, 0)

                for lease in leases:
                    if lease["type"] == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                        ip = lease["ipaddr"]
                        if not ip.startswith("127."):
                            return ip
        except (libvirt.libvirtError, ET.ParseError):
            pass

        time.sleep(1)

    raise SessionError("Guest IP not discovered within 30 seconds")


def create_domain(conn, xml):
    """Create and start a transient domain from XML. On error, raise SessionError."""
    try:
        domain = conn.createXML(xml, 0)
        return domain
    except libvirt.libvirtError as e:
        raise SessionError(f"Failed to create domain: {e}") from e


def destroy_domain(domain):
    """Destroy a domain. Suppress libvirtError (domain may already be gone)."""
    with contextlib.suppress(libvirt.libvirtError):
        domain.destroy()


def cleanup_stale_domain(conn, name):
    """Look up domain by name, destroy if it exists. Suppress all errors."""
    try:
        domain = conn.lookupByName(name)
        destroy_domain(domain)
    except libvirt.libvirtError:
        pass
