## Requirements

### Requirement: Infrastructure packages installed
The base Ansible role SHALL install the following packages using `ansible.builtin.package` for OS-agnostic package management: `openssh-server` (or `openssh` on non-RedHat), `rsync`, `socat`, `tmux`, `git`, and `jq`.

#### Scenario: All packages present after build
- **WHEN** the base role completes
- **THEN** all six infrastructure packages are installed in the image

### Requirement: SSH daemon enabled and configured for passwordless root access
The base role SHALL enable sshd, configure it to permit root login with empty passwords (`PermitRootLogin yes`, `PasswordAuthentication yes`, `PermitEmptyPasswords yes`, `PerSourcePenalties no`), delete the root password, and restart sshd.

#### Scenario: Passwordless root SSH works
- **WHEN** a session connects to the guest via SSH as root with no password
- **THEN** the connection succeeds without prompting for credentials

#### Scenario: sshd enabled at boot
- **WHEN** the guest VM boots from the built image
- **THEN** sshd starts automatically

### Requirement: isolagent directory tree created
The base role SHALL create `/isolagent` and `/isolagent/project` directories with mode `0755`.

#### Scenario: Directories exist after build
- **WHEN** the base role completes
- **THEN** `/isolagent` and `/isolagent/project` exist as directories with mode `0755`
