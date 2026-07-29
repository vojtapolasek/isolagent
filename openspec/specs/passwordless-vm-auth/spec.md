## Requirements

### Requirement: Passwordless SSH authentication for sandbox VMs
The sandbox VM image SHALL be configured at build time to accept SSH connections from the host without any credentials. The `base` Ansible role SHALL configure sshd with `PermitEmptyPasswords yes`, `PasswordAuthentication yes`, `PermitRootLogin yes`, and delete root's password. OS-specific PAM workarounds (e.g., `UsePAM no` on Fedora) SHALL be handled by the OS role, not the base role.

#### Scenario: Host connects to sandbox VM without credentials
- **WHEN** a session boots a sandbox VM from a built image
- **THEN** `ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes root@<guest_ip>` connects successfully without any key file or password

#### Scenario: SSH client skips host key probing
- **WHEN** the session SSH command runs
- **THEN** it includes `-o IdentitiesOnly=yes` to prevent trying keys from `~/.ssh/`

#### Scenario: sshd accepts none auth
- **WHEN** the SSH client sends the initial "none" authentication request
- **THEN** the server accepts it because `PermitEmptyPasswords yes` and `PasswordAuthentication yes` are set and root has no password
