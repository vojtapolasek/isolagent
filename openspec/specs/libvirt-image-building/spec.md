## ADDED Requirements

### Requirement: Build images via libvirt domain lifecycle
The `isolagent build` command SHALL build images by uploading the downloaded base cloud image into the storage pool as `isolagent-<profile>`, creating a transient libvirt domain that boots directly from that volume (no overlay), provisioning it with Ansible over SSH, and destroying the domain. Ansible's changes are written directly to the pool volume, so after domain destruction the volume is the built image. If the build fails, the volume SHALL be deleted so the user can retry. The build SHALL reuse the session runner's `find_iso_tool()` for ISO tool discovery and `wait_for_ssh()` for SSH polling. The builder uses its own cloud-init content (temporary root password for build-time SSH access via `sshpass`) and passes a `sshpass`-wrapped SSH command to `wait_for_ssh()`.

#### Scenario: Successful build
- **WHEN** the user runs `isolagent build myprofile`
- **THEN** the base image is uploaded to the pool as `isolagent-myprofile`, a domain boots from it, Ansible provisions it, and the domain is destroyed — leaving `isolagent-myprofile` as the built image

#### Scenario: Build failure cleanup
- **WHEN** `ansible-playbook` fails or the domain fails to boot
- **THEN** the domain is destroyed (if running) and the `isolagent-myprofile` volume is deleted from the pool

#### Scenario: Build uses same domain configuration as runtime
- **WHEN** a build domain is created
- **THEN** it uses the same machine type (q35), KVM acceleration, virtio devices, and default network as runtime domains

### Requirement: Cloud-init for build-time SSH access
The build process SHALL generate a cloud-init ISO that sets a temporary root password and enables password-based SSH authentication. The temporary password SHALL be removed by the `base` Ansible role during provisioning (`passwd -d root`), so it does not persist in the final image.

#### Scenario: Build SSH access
- **WHEN** the build domain boots
- **THEN** cloud-init sets a temporary root password and the build process connects via SSH with that password

#### Scenario: Password removed after provisioning
- **WHEN** the `base` Ansible role runs during provisioning
- **THEN** the root password is cleared (`passwd -d root`) and the permanent sshd config (`01-isolagent.conf`) supersedes the build-time cloud-init config

### Requirement: Run Ansible provisioner directly
The build process SHALL invoke `ansible-playbook` as a subprocess against the build VM over SSH, using the dynamically generated playbook and roles path from the profile. It SHALL NOT use Packer or any Packer plugins.

#### Scenario: Ansible provisioning
- **WHEN** SSH is available on the build domain
- **THEN** `ansible-playbook` runs with the generated playbook, profile roles, and the VM's IP as the inventory host

#### Scenario: Provisioning failure
- **WHEN** `ansible-playbook` exits with a non-zero code
- **THEN** the build domain is destroyed, the build volume is cleaned up, and the build exits with an error

### Requirement: Store built images as storage pool volumes
The build process SHALL store the resulting disk image as a volume in the libvirt storage pool. The volume name SHALL be `isolagent-<profile>`. If a volume with that name already exists and `--force` is passed (or the user confirms), the existing volume SHALL be deleted before the new one is stored.

#### Scenario: Image stored in pool
- **WHEN** a build completes successfully
- **THEN** a volume named `isolagent-myprofile` exists in the storage pool

#### Scenario: Rebuild with --force
- **WHEN** `isolagent build myprofile --force` is run and `isolagent-myprofile` already exists
- **THEN** the existing volume is deleted and the new image replaces it

#### Scenario: Rebuild without --force
- **WHEN** `isolagent build myprofile` is run and `isolagent-myprofile` already exists
- **THEN** the user is prompted for confirmation before rebuilding

### Requirement: Download base cloud image
The build process SHALL download the base cloud image specified by the OS role's `base_image_url` if not already cached. Downloaded images SHALL be cached in `$XDG_CACHE_HOME/isolagent/` (defaulting to `~/.cache/isolagent/`). If the OS role provides `base_image_sha256`, the download SHALL be verified against that hash.

#### Scenario: First download
- **WHEN** `isolagent build myprofile` runs and the base image is not cached
- **THEN** the image is downloaded to `~/.cache/isolagent/`

#### Scenario: Image already cached
- **WHEN** the base image URL matches a previously downloaded file in the cache
- **THEN** the download is skipped

#### Scenario: SHA-256 verification
- **WHEN** the OS role provides `base_image_sha256`
- **THEN** the downloaded image hash is verified and the build fails on mismatch

### Requirement: Build preflight checks
The build process SHALL verify that libvirtd is reachable, the default network is active, the `default` storage pool exists and is active, `ansible-playbook` is available, an ISO creation tool is available, and `/dev/kvm` exists.

#### Scenario: Missing ansible-playbook
- **WHEN** `ansible-playbook` is not in PATH
- **THEN** the build prints an error with install instructions and exits

#### Scenario: Missing KVM
- **WHEN** `/dev/kvm` does not exist
- **THEN** the build prints an error explaining KVM is required and exits

#### Scenario: libvirtd not reachable
- **WHEN** `libvirt.open()` fails
- **THEN** the build prints an error with instructions to start libvirtd
