## ADDED Requirements

### Requirement: OS role vars define base image and hash
The Fedora OS role's `vars/main.yaml` SHALL define `base_image_url` pointing to the official Fedora Cloud qcow2 image and `base_image_sha256` with the image's SHA-256 hash for integrity verification during download.

#### Scenario: Builder reads OS role vars
- **WHEN** a profile has `image.os: fedora`
- **THEN** the builder loads `roles/fedora/vars/main.yaml` to obtain the download URL and hash

### Requirement: Disable PAM for sshd
The Fedora role SHALL append `UsePAM no` to the isolagent sshd config (`/etc/ssh/sshd_config.d/01-isolagent.conf`). Fedora's `pam_unix.so` rejects empty passwords by default, and this override is required for passwordless SSH access to work.

#### Scenario: Empty password login works
- **WHEN** the Fedora role has run and sshd is restarted
- **THEN** SSH login as root with no password succeeds

### Requirement: SELinux relabel after provisioning
The Fedora role SHALL run `fixfiles -T 0 restore` to relabel the filesystem for SELinux after Ansible provisioning has modified files.

#### Scenario: SELinux contexts restored
- **WHEN** the Fedora role runs
- **THEN** `fixfiles restore` runs so SELinux contexts are correct for all provisioned files

### Requirement: Remove build-time NetworkManager connection profiles
The Fedora role SHALL remove `*.nmconnection` files from `/etc/NetworkManager/system-connections/`. These are created by cloud-init during the build and would conflict with the session-time cloud-init network configuration.

#### Scenario: Stale NM profiles removed
- **WHEN** the Fedora role runs
- **THEN** all `.nmconnection` files in `/etc/NetworkManager/system-connections/` are deleted
