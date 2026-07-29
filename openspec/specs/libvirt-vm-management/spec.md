## ADDED Requirements

### Requirement: Connect to libvirtd via Python API
The session module SHALL connect to the configured libvirt URI (see "Configurable libvirt connection URI" requirement) using `libvirt.open()` during preflight. Connection failures SHALL raise a `SessionError` with instructions to ensure libvirtd is running and the user has appropriate access (e.g., `libvirt` group membership for `qemu:///system`).

#### Scenario: Successful connection
- **WHEN** libvirtd is running and the user has appropriate access
- **THEN** `libvirt.open(uri)` returns a valid connection object

#### Scenario: libvirtd not running
- **WHEN** libvirtd is not running
- **THEN** the session raises `SessionError` with a message instructing the user to start libvirtd

#### Scenario: Connection refused
- **WHEN** the user lacks access to the configured URI (e.g., not in `libvirt` group for `qemu:///system`)
- **THEN** the session raises `SessionError` with a message instructing the user to check their permissions

### Requirement: Generate domain XML from profile settings
The session module SHALL generate a libvirt domain XML document for each VM. The XML SHALL specify: a unique domain name, machine type `q35`, KVM acceleration, vCPU count and memory from the profile's `runtime` section, a virtio disk for the overlay image, a read-only SATA cdrom (`bus='sata'`, `dev='sda'`) for the cloud-init ISO, a virtio-net interface on the `default` network (MAC auto-assigned by libvirt), a vhost-vsock device with auto-assigned CID (`<cid auto='yes'/>`), serial console output to a file, and no display.

#### Scenario: Domain XML with default profile settings
- **WHEN** a profile specifies `runtime.memory: 4G` and `runtime.cpus: 4`
- **THEN** the generated XML contains `<memory unit='GiB'>4</memory>` and `<vcpu>4</vcpu>`

#### Scenario: Domain XML disk configuration
- **WHEN** the overlay is at `/path/overlay.qcow2` and cloud-init ISO at `/tmp/cidata.iso`
- **THEN** the XML contains a virtio disk (`bus='virtio'`) for the overlay and a read-only SATA cdrom (`bus='sata'`, `dev='sda'`) for the cloud-init ISO

#### Scenario: Domain XML network interface
- **WHEN** a domain is created
- **THEN** the XML contains a `<interface type='network'>` with `<source network='default'/>` and no explicit MAC (libvirt auto-assigns one)

#### Scenario: Domain XML vsock device
- **WHEN** a domain is created
- **THEN** the XML contains `<vsock><cid auto='yes'/></vsock>` and the actual CID can be read from the running domain's XML

### Requirement: Generate unique domain names
The session module SHALL generate a unique domain name for each session using the pattern `isolagent-<profile>-<suffix>` where `<suffix>` ensures uniqueness (e.g., a short timestamp or random hex). Domain names SHALL use only characters valid in libvirt domain names (alphanumeric, hyphen, underscore).

#### Scenario: Unique domain name
- **WHEN** two sessions for profile `myprofile` start concurrently
- **THEN** each gets a distinct domain name (e.g., `isolagent-myprofile-a1b2c3` and `isolagent-myprofile-d4e5f6`)

#### Scenario: Domain name used for session identification
- **WHEN** `isolagent list` runs
- **THEN** active sandbox domains are identified by the `isolagent-` prefix in their name

### Requirement: Create and start domain
The session module SHALL create and start a libvirt domain using `conn.createXML(xml, 0)` during the setup phase. If a stale domain with the same name already exists, the session SHALL destroy it before creating the new one.

#### Scenario: Domain creation
- **WHEN** setup runs
- **THEN** a transient domain is created and started with a unique `isolagent-*` name

#### Scenario: Stale domain cleanup
- **WHEN** a domain with the generated name already exists (from a crashed session)
- **THEN** the existing domain is destroyed before the new one is created

### Requirement: Discover guest IP via libvirt API
The session module SHALL discover the guest's IP address after domain creation by polling `domain.interfaceAddresses(VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE)`. If `interfaceAddresses` returns empty (older libvirt), it SHALL fall back to reading the MAC from the running domain's XML and polling `network.DHCPLeases(mac)`. Polling SHALL retry for up to 30 seconds with 1-second intervals before failing.

#### Scenario: IP discovered from DHCP lease
- **WHEN** the domain boots and obtains a DHCP lease
- **THEN** the session discovers the guest IP and records it

#### Scenario: DHCP lease not yet available
- **WHEN** the domain has just started and no lease exists yet
- **THEN** the session retries for up to 30 seconds before raising `SessionError`

### Requirement: Destroy domain on teardown
The session module SHALL destroy the libvirt domain during teardown by calling `domain.destroy()` directly (no graceful shutdown attempt). Errors during destruction (e.g., domain already gone) SHALL be suppressed.

#### Scenario: Domain destroyed
- **WHEN** teardown runs and the domain is still active
- **THEN** `domain.destroy()` forcibly kills the domain immediately

#### Scenario: Domain already gone
- **WHEN** teardown runs but the domain has already been destroyed (e.g., guest crashed)
- **THEN** the teardown continues without error

### Requirement: List sandbox sessions via libvirt
The `isolagent list` command SHALL query `conn.listAllDomains()` and filter by the `isolagent-` naming prefix. For each matching domain, it SHALL display: domain name, profile name (read from the domain's `<metadata>` element), guest IP (from `domain.interfaceAddresses()` or DHCP leases, or "pending" if not yet available), and domain state.

#### Scenario: Active sessions exist
- **WHEN** two sandbox domains are running and the user runs `isolagent list`
- **THEN** the output shows a table with both sessions' name, profile, IP, and state

#### Scenario: No active sessions
- **WHEN** no sandbox domains are running and the user runs `isolagent list`
- **THEN** the output prints "No active sessions"

### Requirement: Manage socat lifecycle via flock
When `runtime.access_host_libvirt` is true, the session module SHALL ensure a host-side socat process is running. Lifecycle is managed via flock on a PID file: exclusive lock for startup serialization (then downgraded to shared), exclusive lock attempt during teardown to decide whether to kill socat. See `vsock-libvirt-bridge` spec for full details.

#### Scenario: First session starts socat
- **WHEN** a session with `runtime.access_host_libvirt: true` starts and no socat is running
- **THEN** socat is started under exclusive lock, PID written, lock downgraded to shared

#### Scenario: Last session stops socat
- **WHEN** a session tears down and the exclusive lock attempt succeeds (no other shared locks held)
- **THEN** socat is killed and the PID file is removed

#### Scenario: Other sessions still active
- **WHEN** a session tears down and the exclusive lock attempt fails (other shared locks held)
- **THEN** socat is left running

### Requirement: Verify default network is active
The session module SHALL verify during preflight that the libvirt `default` network is active. If it is not defined, the error message SHALL instruct the user to ensure libvirt is properly installed. If it is defined but inactive, the error message SHALL instruct the user to run `virsh net-start default`.

#### Scenario: Default network active
- **WHEN** `conn.networkLookupByName('default')` succeeds and the network is active
- **THEN** preflight passes

#### Scenario: Default network inactive
- **WHEN** the `default` network exists but is not active
- **THEN** the session raises `SessionError` with instructions to run `virsh net-start default`

#### Scenario: Default network not defined
- **WHEN** `conn.networkLookupByName('default')` raises `libvirt.libvirtError`
- **THEN** the session raises `SessionError` with instructions to ensure libvirt is properly installed

### Requirement: Configurable libvirt connection URI
The session module SHALL connect to `qemu:///system` by default. The URI SHALL be overridable via the `ISOLAGENT_LIBVIRT_URI` environment variable or the `runtime.libvirt_uri` profile field (environment variable takes precedence). This enables `qemu:///session` and remote URIs.

#### Scenario: Default URI
- **WHEN** no override is set
- **THEN** the session connects to `qemu:///system`

#### Scenario: Environment variable override
- **WHEN** `ISOLAGENT_LIBVIRT_URI=qemu:///session` is set
- **THEN** the session connects to `qemu:///session`

#### Scenario: Profile override
- **WHEN** the profile sets `runtime.libvirt_uri: qemu:///session` and no environment variable is set
- **THEN** the session connects to `qemu:///session`

### Requirement: Manage images via storage pool API
The session module SHALL use the libvirt storage pool API to manage all disk images, using the pool named `default`. If the `default` pool does not exist, preflight SHALL raise a `SessionError` with instructions to create it. Base images are stored as pool volumes after building. Overlays are created as pool volumes with a `<backingStore>` referencing the base image volume. On teardown, overlay volumes are deleted via `vol.delete()`.

#### Scenario: Base image lookup
- **WHEN** preflight checks for a built image
- **THEN** it looks up a volume named `isolagent-<profile>` in the default storage pool

#### Scenario: Base image not found
- **WHEN** the volume `isolagent-<profile>` does not exist in the pool
- **THEN** the session raises `SessionError` with instructions to run `isolagent build` first

#### Scenario: Overlay creation
- **WHEN** init creates an overlay
- **THEN** it creates a pool volume via `pool.createXML()` with `<backingStore>` pointing to the base image volume's path, named `isolagent-<profile>-<suffix>-overlay`

#### Scenario: Overlay deletion on teardown
- **WHEN** teardown runs
- **THEN** the overlay volume is deleted via `vol.delete()`
