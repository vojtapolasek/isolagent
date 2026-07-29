## Requirements

### Requirement: Roles are separated by concern
Ansible roles SHALL be split by concern: base infrastructure, OS-specific configuration, agent installation, libvirt bridge, and profile-specific provisioning. New OS+agent+project combinations SHALL be created by composing roles via the profile's `image.os` and `image.roles` fields.

#### Scenario: Role composition
- **WHEN** a new profile `myproject` is created with `image.os: fedora` and `image.roles: [agent-claude, myproject]`
- **THEN** the builder assembles roles `[base, fedora, agent-claude, myproject]` and generates a playbook applying them in order

#### Scenario: Different OS same agent
- **WHEN** a profile uses `image.os: archlinux` and `image.roles: [agent-claude]`
- **THEN** the builder assembles roles `[base, archlinux, agent-claude]`

### Requirement: Profile data passed as Ansible variables
The builder SHALL pass profile data to Ansible via `--extra-vars`, including `profile_name` and `project_root` (the absolute path to the isolagent project directory). The `ssh_pub_key` variable SHALL NOT be passed, as SSH authentication is handled via passwordless sshd configuration. The `agent_install_command` variable SHALL NOT be passed, as agent installation is handled by agent roles.

#### Scenario: Extra vars passed to Ansible
- **WHEN** `isolagent build example` runs
- **THEN** the Ansible provisioner receives `profile_name` and `project_root` as extra variables

#### Scenario: No ssh_pub_key variable
- **WHEN** `isolagent build` runs
- **THEN** the `ssh_pub_key` variable is NOT passed to Ansible

#### Scenario: No agent_install_command variable
- **WHEN** `isolagent build` runs
- **THEN** the `agent_install_command` variable is NOT passed to Ansible

### Requirement: Passwordless SSH configuration via Ansible
The Ansible `base` role SHALL configure sshd for passwordless "none" authentication and delete root's password. This replaces the previous SSH key injection task.

#### Scenario: sshd configured for passwordless access
- **WHEN** the build completes
- **THEN** the built image has sshd configured with `PermitRootLogin yes`, `PasswordAuthentication yes`, `PermitEmptyPasswords yes`, and `PerSourcePenalties no` (from the base role) and `UsePAM no` (from the fedora role)

#### Scenario: Root password deleted
- **WHEN** the build completes
- **THEN** the root account in the built image has no password set

### Requirement: Service configuration
When `runtime.access_host_libvirt` is `true` in the profile, the Ansible playbook SHALL install the vsock-libvirt-bridge systemd service into the image but leave it disabled by default. Runtime enablement is handled by the session lifecycle. When `runtime.access_host_libvirt` is `false` or absent, the libvirt-bridge role is not included.

#### Scenario: Service installed but disabled
- **WHEN** the build completes for a profile with `runtime.access_host_libvirt: true`
- **THEN** the vsock-libvirt-bridge service unit file exists in the image but `systemctl is-enabled vsock-libvirt-bridge` returns `disabled`
