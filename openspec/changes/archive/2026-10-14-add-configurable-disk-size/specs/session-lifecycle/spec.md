# Spec Delta

## MODIFIED Requirements

### Requirement: Init phase creates ephemeral resources
The init phase SHALL create an overlay as a storage pool volume (with `<backingStore>` referencing the base image volume) with virtual size equal to the resolved `runtime.disk` size, generate a unique domain name, create the cloud-init ISO with DHCP network configuration, and manage the shared socat process for libvirt bridging if `runtime.access_host_libvirt` is true (starting socat only if not already running). Before creating the overlay, the init phase SHALL verify the resolved disk size is not smaller than the base image volume's virtual size and fail with a `SessionError` naming the minimum size if it is. Slot allocation is no longer performed — libvirt handles IP assignment (DHCP) and VSOCK CID assignment (auto).

#### Scenario: Overlay creation
- **WHEN** init runs for profile `myprofile` with suffix `a1b2c3` and `runtime.disk` resolving to "20G"
- **THEN** a pool volume `isolagent-myprofile-a1b2c3-overlay` with virtual size 20 GiB is created backed by the `isolagent-myprofile` base volume

#### Scenario: Disk size below base image minimum
- **WHEN** init runs with a resolved disk size smaller than the base image volume's virtual size
- **THEN** init fails with a `SessionError` naming the minimum size before any overlay volume or domain is created

#### Scenario: Domain name generation
- **WHEN** init runs for profile `myprofile`
- **THEN** a unique domain name like `isolagent-myprofile-<suffix>` is generated

#### Scenario: Libvirt bridge start (first session)
- **WHEN** `runtime.access_host_libvirt` is true and no socat is running
- **THEN** init starts a host socat process and writes its PID to a PID file

#### Scenario: Libvirt bridge reuse (subsequent session)
- **WHEN** `runtime.access_host_libvirt` is true and socat is already running
- **THEN** init skips starting socat

#### Scenario: No libvirt
- **WHEN** `runtime.access_host_libvirt` is false
- **THEN** init does not interact with socat

### Requirement: Setup phase boots VM and provisions runtime
The setup phase SHALL create a transient libvirt domain via `conn.createXML()`, discover the guest IP via DHCP lease polling, wait for SSH, rsync the project into the guest, deploy guest files from the profile's `guest-files/` directory, and enable runtime services. SSH connections SHALL use "none" authentication without any key file or password. The SSH command SHALL include `-o IdentitiesOnly=yes` to prevent SSH from using agent-offered identity keys (ensuring "none" authentication is used). The session cloud-init user-data SHALL preserve root account state (`disable_root: false`, `lock_passwd: false`) and request root partition/filesystem growth, without any SSH key injection or sshd configuration.

#### Scenario: Domain creation
- **WHEN** setup runs
- **THEN** a transient domain is created with KVM, virtio networking on the `default` network, vsock with auto CID, and the overlay disk

#### Scenario: Guest IP discovery
- **WHEN** the domain boots and obtains a DHCP lease
- **THEN** setup discovers the guest IP by polling `domain.interfaceAddresses(VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE)`, falling back to `network.DHCPLeases(mac)` if needed

#### Scenario: SSH readiness
- **WHEN** the guest IP is discovered
- **THEN** setup polls SSH every second for up to 60 seconds before failing

#### Scenario: SSH without credentials
- **WHEN** setup polls or connects via SSH
- **THEN** the SSH command uses no `-i` key file flag and includes `-o IdentitiesOnly=yes`

#### Scenario: Project sync
- **WHEN** SSH is ready
- **THEN** `project.workdir` is rsynced to `/isolagent/project/` on the guest using SSH without key auth

#### Scenario: Guest file deployment
- **WHEN** the profile has a `guest-files/` subdirectory with files
- **THEN** each file is SCP'd to the guest at its mirrored path using SCP without key auth

#### Scenario: No guest files
- **WHEN** the profile has no `guest-files/` subdirectory
- **THEN** setup skips guest file deployment without error

#### Scenario: Libvirt guest service
- **WHEN** `runtime.access_host_libvirt` is true
- **THEN** the vsock-libvirt-bridge service is started on the guest

#### Scenario: Cloud-init user-data content
- **WHEN** the session generates cloud-init user-data
- **THEN** the user-data contains `disable_root: false` and `lock_passwd: false` for root and filesystem-growth directives, with no SSH keys or sshd runcmds

#### Scenario: Domain start failure
- **WHEN** `conn.createXML()` raises a libvirt error
- **THEN** the session raises `SessionError` with the libvirt error message
