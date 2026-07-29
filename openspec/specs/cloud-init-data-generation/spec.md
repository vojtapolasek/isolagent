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
