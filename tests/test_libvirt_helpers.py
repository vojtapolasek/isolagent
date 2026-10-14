import os
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch

import pytest


def _libvirt_available():
    try:
        import libvirt

        conn = libvirt.open("qemu:///system")
        conn.close()
        return True
    except Exception:
        return False


integration = pytest.mark.integration

requires_kvm = pytest.mark.skipif(not os.path.exists("/dev/kvm"), reason="/dev/kvm not available")

requires_libvirt = pytest.mark.skipif(not _libvirt_available(), reason="libvirtd not reachable")


class TestDomainXMLGeneration:
    def test_generates_valid_xml(self):
        from isolagent.libvirt_helpers import generate_domain_xml

        xml = generate_domain_xml(
            name="isolagent-test-abc123",
            memory="4G",
            cpus=4,
            disk_path="/var/lib/libvirt/images/disk.qcow2",
            cloud_init_iso_path="/tmp/cidata.iso",
            console_log_path="/tmp/console.log",
            profile_name="test-profile",
        )

        root = ET.fromstring(xml)
        assert root.tag == "domain"

    def test_correct_memory_4g(self):
        from isolagent.libvirt_helpers import generate_domain_xml

        xml = generate_domain_xml(
            name="isolagent-test-abc123",
            memory="4G",
            cpus=4,
            disk_path="/var/lib/libvirt/images/disk.qcow2",
            cloud_init_iso_path="/tmp/cidata.iso",
            console_log_path="/tmp/console.log",
            profile_name="test-profile",
        )

        root = ET.fromstring(xml)
        mem_elem = root.find("memory")
        assert mem_elem.get("unit") == "GiB"
        assert mem_elem.text == "4"

    def test_correct_memory_512m(self):
        from isolagent.libvirt_helpers import generate_domain_xml

        xml = generate_domain_xml(
            name="isolagent-test-abc123",
            memory="512M",
            cpus=2,
            disk_path="/var/lib/libvirt/images/disk.qcow2",
            cloud_init_iso_path="/tmp/cidata.iso",
            console_log_path="/tmp/console.log",
            profile_name="test-profile",
        )

        root = ET.fromstring(xml)
        mem_elem = root.find("memory")
        assert mem_elem.get("unit") == "MiB"
        assert mem_elem.text == "512"

    def test_correct_vcpu_count(self):
        from isolagent.libvirt_helpers import generate_domain_xml

        xml = generate_domain_xml(
            name="isolagent-test-abc123",
            memory="4G",
            cpus=8,
            disk_path="/var/lib/libvirt/images/disk.qcow2",
            cloud_init_iso_path="/tmp/cidata.iso",
            console_log_path="/tmp/console.log",
            profile_name="test-profile",
        )

        root = ET.fromstring(xml)
        vcpu_elem = root.find("vcpu")
        assert vcpu_elem.text == "8"

    def test_disk_path_in_virtio_disk(self):
        from isolagent.libvirt_helpers import generate_domain_xml

        xml = generate_domain_xml(
            name="isolagent-test-abc123",
            memory="4G",
            cpus=4,
            disk_path="/custom/path/disk.qcow2",
            cloud_init_iso_path="/tmp/cidata.iso",
            console_log_path="/tmp/console.log",
            profile_name="test-profile",
        )

        root = ET.fromstring(xml)
        disk_elem = root.find(".//disk[@device='disk']/source")
        assert disk_elem.get("file") == "/custom/path/disk.qcow2"

    def test_cloud_init_iso_in_cdrom(self):
        from isolagent.libvirt_helpers import generate_domain_xml

        xml = generate_domain_xml(
            name="isolagent-test-abc123",
            memory="4G",
            cpus=4,
            disk_path="/var/lib/libvirt/images/disk.qcow2",
            cloud_init_iso_path="/custom/cidata.iso",
            console_log_path="/tmp/console.log",
            profile_name="test-profile",
        )

        root = ET.fromstring(xml)
        cdrom_elem = root.find(".//disk[@device='cdrom']/source")
        assert cdrom_elem.get("file") == "/custom/cidata.iso"
        readonly = root.find(".//disk[@device='cdrom']/readonly")
        assert readonly is not None
        target = root.find(".//disk[@device='cdrom']/target")
        assert target.get("bus") == "sata"
        assert target.get("dev") == "sda"

    def test_console_log_path_in_serial(self):
        from isolagent.libvirt_helpers import generate_domain_xml

        xml = generate_domain_xml(
            name="isolagent-test-abc123",
            memory="4G",
            cpus=4,
            disk_path="/var/lib/libvirt/images/disk.qcow2",
            cloud_init_iso_path="/tmp/cidata.iso",
            console_log_path="/custom/console.log",
            profile_name="test-profile",
        )

        root = ET.fromstring(xml)
        serial_elem = root.find(".//serial[@type='file']/source")
        assert serial_elem.get("path") == "/custom/console.log"

    def test_vsock_cid_auto(self):
        from isolagent.libvirt_helpers import generate_domain_xml

        xml = generate_domain_xml(
            name="isolagent-test-abc123",
            memory="4G",
            cpus=4,
            disk_path="/var/lib/libvirt/images/disk.qcow2",
            cloud_init_iso_path="/tmp/cidata.iso",
            console_log_path="/tmp/console.log",
            profile_name="test-profile",
        )

        root = ET.fromstring(xml)
        cid_elem = root.find(".//vsock/cid")
        assert cid_elem.get("auto") == "yes"

    def test_profile_name_in_metadata(self):
        from isolagent.libvirt_helpers import generate_domain_xml

        xml = generate_domain_xml(
            name="isolagent-test-abc123",
            memory="4G",
            cpus=4,
            disk_path="/var/lib/libvirt/images/disk.qcow2",
            cloud_init_iso_path="/tmp/cidata.iso",
            console_log_path="/tmp/console.log",
            profile_name="my-test-profile",
        )

        root = ET.fromstring(xml)
        ns = {"isolagent": "http://isolagent.local/"}
        profile_elem = root.find(".//isolagent:profile", ns)
        assert profile_elem.text == "my-test-profile"

    def test_no_explicit_mac_address(self):
        from isolagent.libvirt_helpers import generate_domain_xml

        xml = generate_domain_xml(
            name="isolagent-test-abc123",
            memory="4G",
            cpus=4,
            disk_path="/var/lib/libvirt/images/disk.qcow2",
            cloud_init_iso_path="/tmp/cidata.iso",
            console_log_path="/tmp/console.log",
            profile_name="test-profile",
        )

        root = ET.fromstring(xml)
        mac_elem = root.find(".//interface/mac")
        assert mac_elem is None

    def test_machine_type_is_q35(self):
        from isolagent.libvirt_helpers import generate_domain_xml

        xml = generate_domain_xml(
            name="isolagent-test-abc123",
            memory="4G",
            cpus=4,
            disk_path="/var/lib/libvirt/images/disk.qcow2",
            cloud_init_iso_path="/tmp/cidata.iso",
            console_log_path="/tmp/console.log",
            profile_name="test-profile",
        )

        root = ET.fromstring(xml)
        type_elem = root.find(".//os/type")
        assert type_elem.get("machine") == "q35"


class TestParseSize:
    def test_parses_gigabytes(self):
        from isolagent.libvirt_helpers import parse_size

        assert parse_size("4G") == (4, "GiB")

    def test_parses_megabytes(self):
        from isolagent.libvirt_helpers import parse_size

        assert parse_size("512M") == (512, "MiB")

    def test_parses_terabytes(self):
        from isolagent.libvirt_helpers import parse_size

        assert parse_size("1T") == (1, "TiB")

    def test_strips_whitespace_and_lowercase(self):
        from isolagent.libvirt_helpers import parse_size

        assert parse_size(" 8g ") == (8, "GiB")

    def test_rejects_missing_unit(self):
        from isolagent.libvirt_helpers import parse_size

        with pytest.raises(ValueError, match="Invalid size format"):
            parse_size("40")

    def test_rejects_non_numeric(self):
        from isolagent.libvirt_helpers import parse_size

        with pytest.raises(ValueError, match="Invalid size format"):
            parse_size("big")

    def test_rejects_non_numeric_with_unit(self):
        from isolagent.libvirt_helpers import parse_size

        with pytest.raises(ValueError, match="Invalid size format"):
            parse_size("abcG")


class TestParseSizeBytes:
    def test_gigabytes_to_bytes(self):
        from isolagent.libvirt_helpers import parse_size_bytes

        assert parse_size_bytes("20G") == 20 * 1024**3

    def test_megabytes_to_bytes(self):
        from isolagent.libvirt_helpers import parse_size_bytes

        assert parse_size_bytes("512M") == 512 * 1024**2

    def test_terabytes_to_bytes(self):
        from isolagent.libvirt_helpers import parse_size_bytes

        assert parse_size_bytes("1T") == 1024**4

    def test_malformed_raises(self):
        from isolagent.libvirt_helpers import parse_size_bytes

        with pytest.raises(ValueError, match="Invalid size format"):
            parse_size_bytes("40")


class TestCreateOverlayVolume:
    def _capture_vol_xml(self, capacity_bytes):
        from isolagent.libvirt_helpers import create_overlay_volume

        mock_conn = MagicMock()
        mock_pool = MagicMock()
        with (
            patch(
                "isolagent.libvirt_helpers.get_default_pool",
                return_value=mock_pool,
            ),
            patch(
                "isolagent.libvirt_helpers.get_volume_path",
                return_value="/var/lib/libvirt/images/base.qcow2",
            ),
        ):
            create_overlay_volume(mock_conn, "ov", "base", capacity_bytes)
        vol_xml = mock_pool.createXML.call_args[0][0]
        return ET.fromstring(vol_xml)

    def test_volume_xml_uses_given_capacity(self):
        root = self._capture_vol_xml(40 * 1024**3)
        capacity = root.find("capacity")
        assert capacity.get("unit") == "bytes"
        assert capacity.text == str(40 * 1024**3)

    def test_volume_xml_keeps_backing_store(self):
        root = self._capture_vol_xml(20 * 1024**3)
        backing = root.find(".//backingStore/path")
        assert backing.text == "/var/lib/libvirt/images/base.qcow2"


class TestGetVolumeVirtualSize:
    def _mock_vol(self, xml_capacity):
        mock_pool = MagicMock()
        mock_vol = MagicMock()
        mock_vol.XMLDesc.return_value = (
            f"<volume><name>base</name><capacity unit='bytes'>{xml_capacity}</capacity></volume>"
        )
        mock_pool.storageVolLookupByName.return_value = mock_vol
        return mock_pool, mock_vol

    def test_refreshes_pool_and_returns_capacity(self):
        from isolagent.libvirt_helpers import get_volume_virtual_size

        mock_conn = MagicMock()
        mock_pool, mock_vol = self._mock_vol(5 * 1024**3)
        with patch(
            "isolagent.libvirt_helpers.get_default_pool",
            return_value=mock_pool,
        ):
            size = get_volume_virtual_size(mock_conn, "base")

        mock_pool.refresh.assert_called_once_with(0)
        assert size == 5 * 1024**3

    def test_zero_capacity_raises(self):
        from isolagent.libvirt_helpers import get_volume_virtual_size
        from isolagent.session import SessionError

        mock_conn = MagicMock()
        mock_pool, _ = self._mock_vol(0)
        with (
            patch(
                "isolagent.libvirt_helpers.get_default_pool",
                return_value=mock_pool,
            ),
            pytest.raises(SessionError, match="base"),
        ):
            get_volume_virtual_size(mock_conn, "base")

    def test_libvirt_error_raises(self):
        import libvirt

        from isolagent.libvirt_helpers import get_volume_virtual_size
        from isolagent.session import SessionError

        mock_conn = MagicMock()
        mock_pool = MagicMock()
        mock_pool.refresh.side_effect = libvirt.libvirtError("probe failed")
        with (
            patch(
                "isolagent.libvirt_helpers.get_default_pool",
                return_value=mock_pool,
            ),
            pytest.raises(SessionError, match="base"),
        ):
            get_volume_virtual_size(mock_conn, "base")

    def test_missing_capacity_raises(self):
        from isolagent.libvirt_helpers import get_volume_virtual_size
        from isolagent.session import SessionError

        mock_conn = MagicMock()
        mock_pool = MagicMock()
        mock_vol = MagicMock()
        mock_vol.XMLDesc.return_value = "<volume><name>base</name></volume>"
        mock_pool.storageVolLookupByName.return_value = mock_vol
        with (
            patch(
                "isolagent.libvirt_helpers.get_default_pool",
                return_value=mock_pool,
            ),
            pytest.raises(SessionError, match="base"),
        ):
            get_volume_virtual_size(mock_conn, "base")


class TestDomainNameGeneration:
    def test_returns_correct_format(self):
        from isolagent.libvirt_helpers import generate_domain_name

        name = generate_domain_name("test-profile")
        assert name.startswith("isolagent-test-profile-")
        suffix = name.split("-")[-1]
        assert len(suffix) == 6
        assert all(c in "0123456789abcdef" for c in suffix)

    def test_two_calls_return_different_names(self):
        from isolagent.libvirt_helpers import generate_domain_name

        name1 = generate_domain_name("test-profile")
        name2 = generate_domain_name("test-profile")
        assert name1 != name2

    def test_only_valid_characters(self):
        from isolagent.libvirt_helpers import generate_domain_name

        name = generate_domain_name("test_profile-123")
        assert "isolagent-test_profile-123-" in name

    def test_rejects_invalid_profile_names_spaces(self):
        from isolagent.libvirt_helpers import generate_domain_name

        with pytest.raises(ValueError, match="Invalid profile name"):
            generate_domain_name("test profile")

    def test_rejects_invalid_profile_names_special(self):
        from isolagent.libvirt_helpers import generate_domain_name

        with pytest.raises(ValueError, match="Invalid profile name"):
            generate_domain_name("test@profile")


class TestDHCPLeaseDiscovery:
    def test_returns_ipv4_from_interface_addresses(self, monkeypatch):
        import libvirt

        from isolagent.libvirt_helpers import discover_guest_ip

        mock_domain = MagicMock()
        mock_conn = MagicMock()

        mock_domain.interfaceAddresses.return_value = {
            "vnet0": {"addrs": [{"type": libvirt.VIR_IP_ADDR_TYPE_IPV4, "addr": "192.168.122.50"}]}
        }

        monkeypatch.setattr("time.sleep", lambda s: None)

        ip = discover_guest_ip(mock_domain, mock_conn)
        assert ip == "192.168.122.50"

    def test_falls_back_to_mac_dhcp_leases(self, monkeypatch):
        import libvirt

        from isolagent.libvirt_helpers import discover_guest_ip

        mock_domain = MagicMock()
        mock_conn = MagicMock()

        mock_domain.interfaceAddresses.return_value = {}
        mock_domain.XMLDesc.return_value = """
<domain>
  <devices>
    <interface type='network'>
      <mac address='52:54:00:12:34:56'/>
    </interface>
  </devices>
</domain>
"""

        mock_network = MagicMock()
        mock_network.DHCPLeases.return_value = [
            {"type": libvirt.VIR_IP_ADDR_TYPE_IPV4, "ipaddr": "192.168.122.100"}
        ]
        mock_conn.networkLookupByName.return_value = mock_network

        monkeypatch.setattr("time.sleep", lambda s: None)

        ip = discover_guest_ip(mock_domain, mock_conn)
        assert ip == "192.168.122.100"

    def test_raises_after_30s_timeout(self, monkeypatch):
        import libvirt

        from isolagent.libvirt_helpers import discover_guest_ip
        from isolagent.session import SessionError

        mock_domain = MagicMock()
        mock_conn = MagicMock()

        mock_domain.interfaceAddresses.return_value = {}
        mock_domain.XMLDesc.side_effect = libvirt.libvirtError("not found")

        real_time = __import__("time").time
        start_time = [real_time()]

        def fake_time():
            start_time[0] += 2
            return start_time[0]

        monkeypatch.setattr("time.time", fake_time)
        monkeypatch.setattr("time.sleep", lambda s: None)

        with pytest.raises(SessionError, match="Guest IP not discovered"):
            discover_guest_ip(mock_domain, mock_conn)


class TestCmdListViaLibvirt:
    def test_shows_table_output(self, capsys):
        import libvirt

        from isolagent.cli import cmd_list

        mock_conn = MagicMock()
        mock_domain1 = MagicMock()
        mock_domain1.name.return_value = "isolagent-test-abc123"
        mock_domain1.state.return_value = (1, 0)
        mock_domain1.XMLDesc.return_value = """
<domain>
  <metadata>
    <isolagent:profile xmlns:isolagent="http://isolagent.local/">test-profile</isolagent:profile>
  </metadata>
</domain>
"""
        mock_domain1.interfaceAddresses.return_value = {
            "vnet0": {"addrs": [{"type": libvirt.VIR_IP_ADDR_TYPE_IPV4, "addr": "192.168.122.50"}]}
        }

        mock_domain2 = MagicMock()
        mock_domain2.name.return_value = "isolagent-dev-def456"
        mock_domain2.state.return_value = (1, 0)
        mock_domain2.XMLDesc.return_value = """
<domain>
  <metadata>
    <isolagent:profile xmlns:isolagent="http://isolagent.local/">dev-profile</isolagent:profile>
  </metadata>
</domain>
"""
        mock_domain2.interfaceAddresses.return_value = {
            "vnet1": {"addrs": [{"type": libvirt.VIR_IP_ADDR_TYPE_IPV4, "addr": "192.168.122.51"}]}
        }

        mock_conn.listAllDomains.return_value = [mock_domain1, mock_domain2]

        with patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn):
            cmd_list(None)

        output = capsys.readouterr().out
        assert "isolagent-test-abc123" in output
        assert "test-profile" in output
        assert "192.168.122.50" in output
        assert "isolagent-dev-def456" in output
        assert "dev-profile" in output

    def test_no_domains_prints_message(self, capsys):
        from isolagent.cli import cmd_list

        mock_conn = MagicMock()
        mock_conn.listAllDomains.return_value = []

        with patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn):
            cmd_list(None)

        output = capsys.readouterr().out
        assert "No active sessions" in output


@integration
@requires_libvirt
class TestStoragePoolVolumeManagement:
    def _create_dummy_volume(self, conn, name):
        pool = conn.storagePoolLookupByName("default")
        vol_xml = f"""<volume>
  <name>{name}</name>
  <capacity unit='bytes'>1048576</capacity>
  <target><format type='qcow2'/></target>
</volume>"""
        return pool.createXML(vol_xml, 0)

    def test_volume_exists_and_not_exists(self):
        from isolagent.libvirt_helpers import (
            generate_domain_name,
            get_libvirt_connection,
            volume_exists,
        )

        vol_name = generate_domain_name("test-vol")
        conn = get_libvirt_connection()
        try:
            assert volume_exists(conn, vol_name) is False
            self._create_dummy_volume(conn, vol_name)
            assert volume_exists(conn, vol_name) is True
        finally:
            try:
                pool = conn.storagePoolLookupByName("default")
                vol = pool.storageVolLookupByName(vol_name)
                vol.delete(0)
            except Exception:
                pass
            conn.close()

    def test_delete_volume_removes_and_suppresses_errors(self):
        from isolagent.libvirt_helpers import (
            delete_volume,
            generate_domain_name,
            get_libvirt_connection,
            volume_exists,
        )

        vol_name = generate_domain_name("test-del")
        conn = get_libvirt_connection()
        try:
            self._create_dummy_volume(conn, vol_name)
            assert volume_exists(conn, vol_name) is True
            delete_volume(conn, vol_name)
            assert volume_exists(conn, vol_name) is False
            delete_volume(conn, "nonexistent-vol-that-does-not-exist")
        finally:
            try:
                pool = conn.storagePoolLookupByName("default")
                vol = pool.storageVolLookupByName(vol_name)
                vol.delete(0)
            except Exception:
                pass
            conn.close()

    def test_create_overlay_volume_creates_with_backing_store(self):
        import xml.etree.ElementTree as ET

        from isolagent.libvirt_helpers import (
            create_overlay_volume,
            generate_domain_name,
            get_libvirt_connection,
            volume_exists,
        )

        base_name = generate_domain_name("test-base")
        overlay_name = generate_domain_name("test-overlay")
        conn = get_libvirt_connection()
        try:
            self._create_dummy_volume(conn, base_name)
            create_overlay_volume(conn, overlay_name, base_name, 1024 * 1024 * 1024)
            assert volume_exists(conn, overlay_name) is True

            pool = conn.storagePoolLookupByName("default")
            overlay_vol = pool.storageVolLookupByName(overlay_name)
            overlay_xml = overlay_vol.XMLDesc(0)
            root = ET.fromstring(overlay_xml)
            backing = root.find(".//backingStore/path")
            assert backing is not None
            assert base_name in backing.text
        finally:
            for name in (overlay_name, base_name):
                try:
                    pool = conn.storagePoolLookupByName("default")
                    vol = pool.storageVolLookupByName(name)
                    vol.delete(0)
                except Exception:
                    pass
            conn.close()


@integration
@requires_kvm
@requires_libvirt
class TestDomainXMLValidation:
    def test_generated_xml_accepted_by_libvirt(self):
        from isolagent.libvirt_helpers import (
            generate_domain_name,
            generate_domain_xml,
            get_libvirt_connection,
        )

        name = generate_domain_name("xmltest")
        xml = generate_domain_xml(
            name=name,
            memory="1G",
            cpus=1,
            disk_path="/nonexistent/dummy.qcow2",
            cloud_init_iso_path="/nonexistent/cidata.iso",
            console_log_path="/nonexistent/console.log",
            profile_name="xmltest",
        )

        conn = get_libvirt_connection()
        dom = None
        try:
            dom = conn.defineXMLFlags(xml, 0)
            assert dom is not None
        finally:
            if dom is not None:
                dom.undefine()
            conn.close()
