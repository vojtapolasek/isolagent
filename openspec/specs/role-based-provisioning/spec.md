## Requirements

### Requirement: Fixed role ordering
The system SHALL apply roles in a fixed order: base (infrastructure), OS-specific, libvirt-bridge (conditional on `runtime.access_host_libvirt`), then profile-listed roles.

#### Scenario: Full role list with libvirt bridge
- **WHEN** a profile has `image.os: fedora`, `runtime.access_host_libvirt: true`, and `image.roles: [agent-claude, example]`
- **THEN** the assembled role list is `[base, fedora, libvirt-bridge, agent-claude, example]`

#### Scenario: Role list without libvirt bridge
- **WHEN** a profile has `image.os: fedora`, `runtime.access_host_libvirt: false`, and `image.roles: [agent-claude]`
- **THEN** the assembled role list is `[base, fedora, agent-claude]`

### Requirement: Base role installs only sandbox infrastructure
The `base` role SHALL install only packages required for sandbox operation: `openssh-server`, `rsync`, `socat`, `tmux`, `git`, `jq`. It SHALL use `ansible.builtin.package` for OS-agnostic package management.

#### Scenario: Base role package list
- **WHEN** the `base` role is applied to any OS
- **THEN** it installs exactly: `openssh-server` (or OS equivalent), `rsync`, `socat`, `tmux`, `git`, `jq`

#### Scenario: OS-agnostic package module
- **WHEN** the `base` role runs on Fedora
- **THEN** it uses `ansible.builtin.package`, not `ansible.builtin.dnf`

### Requirement: Base role configures SSH access and isolagent directory
The `base` role SHALL enable sshd with passwordless root access and create the `/isolagent` directory.

#### Scenario: SSH configuration
- **WHEN** the `base` role is applied
- **THEN** sshd is enabled with `PermitEmptyPasswords yes`, `PasswordAuthentication yes`, `PermitRootLogin yes`, `PerSourcePenalties no`, and root's password is deleted

#### Scenario: Sandbox directory
- **WHEN** the `base` role is applied
- **THEN** `/isolagent` exists as a directory with mode 0755

### Requirement: OS roles carry base image metadata
Each OS role SHALL contain `vars/main.yaml` with `base_image_url` (string) and `base_image_sha256` (string, optional). The builder SHALL read these values to download the correct base image.

#### Scenario: Fedora OS role vars
- **WHEN** the `fedora` role's `vars/main.yaml` contains `base_image_url` and `base_image_sha256`
- **THEN** the builder uses these values for image download and verification

#### Scenario: Missing base_image_url in OS role
- **WHEN** an OS role's `vars/main.yaml` is missing `base_image_url`
- **THEN** the builder fails with an error identifying the missing field and the OS role name

### Requirement: OS roles handle OS-specific configuration
Each OS role SHALL handle configuration specific to that operating system, including package manager differences, security frameworks, and cleanup tasks.

#### Scenario: Fedora SELinux relabel
- **WHEN** the `fedora` role is applied
- **THEN** it runs `fixfiles -T 0 restore` for SELinux relabeling

#### Scenario: Fedora NetworkManager cleanup
- **WHEN** the `fedora` role is applied
- **THEN** it removes build-time NetworkManager connection profiles from `/etc/NetworkManager/system-connections/`

### Requirement: Agent roles hardcode installation
Each agent role SHALL contain its install command directly in `tasks/main.yaml` with idempotent execution. Shell-based roles SHALL use a `creates` guard; copy-based roles rely on the module's built-in idempotency. The install command SHALL NOT be parameterized via extra vars.

#### Scenario: Claude agent role
- **WHEN** the `agent-claude` role is applied
- **THEN** it installs Claude Code using a hardcoded shell command with `creates: /usr/local/bin/claude`

#### Scenario: Test agent role
- **WHEN** the `agent-test` role is applied
- **THEN** it copies the test agent script to `/usr/local/bin/agent-test` using an idempotent copy

### Requirement: Libvirt-bridge role is included automatically
The `libvirt-bridge` role SHALL be included automatically when `runtime.access_host_libvirt` is `true` in the profile. It SHALL NOT appear in the profile's `image.roles` list.

#### Scenario: Auto-included
- **WHEN** a profile has `runtime.access_host_libvirt: true`
- **THEN** the `libvirt-bridge` role is included after the OS role and before profile-listed roles

#### Scenario: Not included
- **WHEN** a profile has `runtime.access_host_libvirt: false`
- **THEN** the `libvirt-bridge` role is not included

### Requirement: Profile-specific roles live in the profile directory
Profile-specific roles SHALL be stored in a `roles/` subdirectory within the profile directory. Role resolution SHALL search the profile's `roles/` directory before the global `roles/` directory.

#### Scenario: Profile-local role resolution
- **WHEN** a profile at `profiles/example/` lists `image.roles: [example]`
- **THEN** the system finds the role at `profiles/example/roles/example/`

#### Scenario: Profile-local takes precedence over global
- **WHEN** a role name exists in both `profiles/myprofile/roles/` and `roles/`
- **THEN** the profile-local version is used

### Requirement: Global roles live in a top-level roles directory
Shared roles (`base`, OS roles, agent roles, `libvirt-bridge`) SHALL be stored in a top-level `roles/` directory in the project root.

#### Scenario: Global role location
- **WHEN** the builder looks for the `base` role
- **THEN** it finds it at `roles/base/`
