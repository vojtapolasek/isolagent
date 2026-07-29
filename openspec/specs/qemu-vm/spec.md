## ADDED Requirements

### Requirement: QEMU VM launch
The VM launch is handled by `isolagent/session.py` using the libvirt Python API. The session module SHALL create a transient libvirt domain with a q35 machine, virtio-net on the `default` libvirt network, and `vhost-vsock-pci` with auto-assigned CID. The vsock device is always present in the domain XML regardless of whether `runtime.access_host_libvirt` is true. Memory and CPU count come from the profile's `runtime` section.

#### Scenario: Default launch
- **WHEN** `isolagent run myprofile` is invoked
- **THEN** a libvirt domain is created with an auto-assigned VSOCK CID, using the profile's memory and CPU settings, on the `default` libvirt network

#### Scenario: Runtime overrides
- **WHEN** `isolagent run myprofile --memory 8G --cpus 8` is invoked
- **THEN** the domain is created with 8G memory and 8 vCPUs instead of the profile defaults

### Requirement: DHCP via cloud-init
The guest network SHALL be configured via DHCP on the libvirt default network. Cloud-init SHALL use a network config that enables DHCP on the primary interface. The guest IP SHALL be discovered after boot via the libvirt DHCP lease API.

#### Scenario: Network available after boot
- **WHEN** the VM boots and cloud-init runs
- **THEN** the guest obtains an IP via DHCP from libvirt's dnsmasq and can reach the host and the internet

### Requirement: Unprivileged QEMU execution
VM launch SHALL NOT require root or sudo. The user SHALL be a member of the `libvirt` group. The QEMU process SHALL be started by libvirtd and run as the `qemu` user with SELinux sVirt confinement, seccomp filtering, and cgroup limits applied automatically by libvirt's security drivers.

#### Scenario: Non-root user launches VM
- **WHEN** a non-root user in the `libvirt` group runs `isolagent run myprofile`
- **THEN** the VM starts successfully without any sudo prompts

### Requirement: Ephemeral overlay disk
The overlay SHALL be created as a storage pool volume backed by the profile's base image volume. The overlay volume SHALL be deleted via `vol.delete()` during teardown.

#### Scenario: Clean slate per run
- **WHEN** `isolagent run myprofile` launches a session
- **THEN** a new overlay pool volume is created backed by `isolagent-myprofile`
- **WHEN** the session ends
- **THEN** the overlay volume is deleted from the pool

### Requirement: VM cleanup on exit
The session module SHALL ensure the libvirt domain, host-side socat, overlay pool volume, and ephemeral files are cleaned up when the session ends, including on errors and signals. Domain cleanup SHALL use `domain.destroy()` directly.

#### Scenario: Ctrl+C during session
- **WHEN** the user presses Ctrl+C during the agent session
- **THEN** the session teardown runs: the domain is destroyed, overlay volume is deleted, socat is stopped (if last session and `runtime.access_host_libvirt` is true), and temp files are deleted
