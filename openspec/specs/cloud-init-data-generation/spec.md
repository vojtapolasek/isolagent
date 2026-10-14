## Requirements

### Requirement: Build VM cloud-init uses password-based SSH
The builder SHALL generate a cloud-init user-data payload that enables SSH password authentication for root with a hardcoded build password (`isolagent-build`). It SHALL configure `PermitRootLogin yes` and restart sshd via `runcmd`. The meta-data SHALL set instance-id to `isolagent-build` and local-hostname to `isolagent`.

#### Scenario: Builder SSH access
- **WHEN** `isolagent build <profile>` boots the build VM
- **THEN** Ansible can connect via SSH as root using the build password

#### Scenario: Build cloud-init does not persist
- **WHEN** the build completes and the base role runs
- **THEN** the base role removes the build-time SSH config (`00-isolagent-build.conf`) and writes its own passwordless access config (`01-isolagent.conf`) for the final image

### Requirement: Session VM cloud-init uses passwordless root
The session SHALL generate a cloud-init user-data payload that disables root lockout (`disable_root: false`) and unlocks the root account (`lock_passwd: false`). It SHALL NOT set a password or inject SSH keys — the built image already has passwordless SSH configured by the base role.

#### Scenario: Session SSH access
- **WHEN** a session VM boots
- **THEN** the session connects via plain SSH as root with empty-password authentication (the base role configured `PermitEmptyPasswords yes` and deleted root's password with `passwd -d root`)

### Requirement: Session cloud-init includes network configuration
The session SHALL generate a netplan-style network-config that enables DHCP on all `en*` interfaces. This ensures the guest obtains an IP address on the libvirt default network.

#### Scenario: Guest gets DHCP lease
- **WHEN** a session VM boots with the cloud-init network config
- **THEN** the guest acquires an IPv4 address via DHCP from the libvirt default network

### Requirement: Cloud-init ISO generated from data files
Both the builder and session SHALL write cloud-init data files (user-data, meta-data, and optionally network-config) to a temporary directory and generate a `cidata` ISO using an available ISO creation tool (`genisoimage`, `mkisofs`, or `xorrisofs`). The ISO is attached to the VM as a cdrom device.

#### Scenario: ISO contains all data files
- **WHEN** the cloud-init ISO is generated
- **THEN** it contains user-data and meta-data (and network-config for sessions) with volume ID `cidata`

### Requirement: Session cloud-init grows root filesystem
The session SHALL generate cloud-init user-data that grows the root partition into the enlarged disk and resizes the root filesystem to fill it (cloud-init `growpart` in automatic mode on the root device, plus root filesystem resize). Because each session's cloud-init meta-data uses a fresh unique instance-id, the growth modules SHALL execute on every session boot. The growth directives SHALL be idempotent: when the root filesystem already occupies the available space, boot proceeds unchanged.

#### Scenario: Root filesystem expands to configured size
- **WHEN** a session VM boots on an overlay whose virtual size exceeds the base image's root filesystem size
- **THEN** the root partition and root filesystem are grown and `df` inside the guest reports the configured size (within filesystem overhead)

#### Scenario: Growth is a no-op when disk equals base size
- **WHEN** a session VM boots on an overlay whose virtual size equals the base image's disk size
- **THEN** cloud-init growth modules complete without error and the root filesystem is unchanged

#### Scenario: Build-time user-data unaffected
- **WHEN** the builder generates its cloud-init user-data
- **THEN** the payload is unchanged by this capability (build VM disk growth is out of scope)
