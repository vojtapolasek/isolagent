## Requirements

### Requirement: Build preflight validates prerequisites
The `isolagent build` command SHALL run a preflight check before starting the build. The check SHALL verify all of the following and exit with code 1 on the first failure, printing a human-readable error with install instructions where applicable.

#### Scenario: libvirt connection
- **WHEN** libvirtd is not running or not accessible
- **THEN** the build exits with an error identifying the libvirt connection failure

#### Scenario: Default network
- **WHEN** the libvirt default network does not exist or is not active
- **THEN** the build exits with an error about the missing/inactive default network

#### Scenario: Default storage pool
- **WHEN** the libvirt default storage pool does not exist
- **THEN** the build exits with an error about the missing storage pool

#### Scenario: ansible-playbook not in PATH
- **WHEN** `ansible-playbook` is not found in `$PATH`
- **THEN** the build exits with an error and suggests `dnf install ansible-core` or `pacman -S ansible`

#### Scenario: No ISO creation tool
- **WHEN** none of `genisoimage`, `mkisofs`, or `xorrisofs` is found in `$PATH`
- **THEN** the build exits listing all three as install options

#### Scenario: /dev/kvm not available
- **WHEN** `/dev/kvm` does not exist
- **THEN** the build exits with an error stating KVM is required

#### Scenario: sshpass not in PATH
- **WHEN** `sshpass` is not found in `$PATH`
- **THEN** the build exits with an error and suggests `dnf install sshpass` or `pacman -S sshpass`

#### Scenario: All checks pass
- **WHEN** all prerequisites are met
- **THEN** the build proceeds to image creation
