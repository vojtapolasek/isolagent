# Host Network Setup

The sandbox uses libvirt's default network for VM networking. No custom bridge or firewalld configuration is required.

## Prerequisites

| Requirement | Description |
|-------------|-------------|
| libvirtd running | `systemctl status libvirtd` (system) or `systemctl --user status libvirtd` (rootless) |
| User in `libvirt` group | `groups` should include `libvirt` for qemu:///system access |
| Default network active | `virsh net-list --all` should show `default` as active |

Add yourself to the `libvirt` group:

```shell
sudo usermod -a -G libvirt $USER
# Log out and back in for the group change to take effect
```

Start libvirtd if not running:

```shell
# System-wide (requires libvirt group membership)
sudo systemctl enable --now libvirtd

# Rootless (no group membership needed)
systemctl --user enable --now libvirtd
```

Ensure the default network is active:

```shell
virsh net-start default       # system-wide
virsh -c qemu:///session net-start default  # rootless
```

## Libvirt URI

The sandbox defaults to `qemu:///system`, which provides the best compatibility and performance. `qemu:///session` (rootless) is supported but has not been tested yet. Set the `ISOLAGENT_LIBVIRT_URI` environment variable or the `runtime.libvirt_uri` profile field to use a different URI:

```shell
# Rootless operation (no group membership needed)
export ISOLAGENT_LIBVIRT_URI=qemu:///session
isolagent run <profile> --output-mode patch
```

Profile field:

```yaml
runtime:
  libvirt_uri: qemu:///session
```

## Networking Details

libvirt's default network provides:

- **Bridge:** `virbr0` (created and managed by libvirt)
- **Subnet:** `192.168.122.0/24`
- **DHCP:** Automatic IP assignment for VMs
- **NAT:** Internet access via masquerade
- **Isolation:** VMs are isolated from the host's default network by nftables rules

The sandbox queries libvirt's DHCP leases to discover each VM's IP address after boot.
