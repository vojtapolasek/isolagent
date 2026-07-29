# Image Building

`isolagent build <profile>` creates a prebaked qcow2 VM image using libvirt and Ansible. The image contains the base OS, the agent binary, and system packages. Build once per profile; rebuild when dependencies change.

## Prerequisites

| Tool | Fedora | Arch |
|------|--------|------|
| libvirt-python | `dnf install python3-libvirt` | `pacman -S python-libvirt` |
| Ansible | `dnf install ansible-core` | `pacman -S ansible` |
| sshpass | `dnf install sshpass` | `pacman -S sshpass` |
| KVM | `/dev/kvm` must exist (hardware virtualization enabled in BIOS) | same |
| ISO tool | `genisoimage`, `mkisofs`, or `xorrisofs` (one of these must be in PATH) | same |

## Build Command

```shell
isolagent build opencode-quickstart
```

Add `--force` to skip the rebuild confirmation prompt:

```shell
isolagent build opencode-quickstart --force
```

Use `--profiles-dir` to load profiles from a non-default location:

```shell
isolagent build opencode-quickstart --profiles-dir /path/to/profiles
```

## How the Build Works

### Step 1: Read OS role metadata

The OS role specified by `image.os` in the profile is loaded from `roles/<os>/vars/main.yaml`. This provides the base cloud image URL and optional SHA-256 hash.

### Step 2: Download base image

The cloud image URL from the OS role vars is downloaded to `~/.cache/isolagent/`. Subsequent builds reuse the cached download. If a SHA-256 hash is provided, downloads are verified.

### Step 3: Upload base image to libvirt storage pool

The downloaded cloud image is uploaded to libvirt's default storage pool as a new volume. If the volume already exists, it is reused.

### Step 4: Generate playbook and boot build VM

The builder assembles the role list and generates a temporary Ansible playbook. A build VM is created from the base image volume with cloud-init configuration (root password for SSH access). The VM boots and the builder waits for SSH to become available.

**Role ordering:** `base` → OS role → `libvirt-bridge` (if `runtime.access_host_libvirt: true`) → profile-listed roles from `image.roles`.

Ansible receives these extra variables for the playbook:

| Variable | Value |
|----------|-------|
| `profile_name` | The profile's `name` field |
| `project_root` | Absolute path to this project |

The `ANSIBLE_ROLES_PATH` environment variable is set to search the profile's local `roles/` directory first, then the global `roles/` directory.

Ansible connects to the build VM using password authentication via `sshpass` (the cloud-init root password).

### Step 5: Destroy build VM and commit image

After provisioning completes, the build VM domain is destroyed. The modified disk becomes the immutable base image volume for the profile.

## What Gets Baked vs. Session-Time

| Baked into image (build time) | Applied at session start (run time) |
|-------------------------------|--------------------------------------|
| OS packages | Project files (rsync) |
| Agent binary | Guest files (SCP from profile's `guest-files/`) |
| SSH authorized_keys | Cloud-init network config (DHCP) |
| systemd services (vsock bridge) | libvirt overlay volume creation |
| SELinux relabeling (Fedora) | Inline `agent.env` injection |

## Role Structure

Roles live in the top-level `roles/` directory. Profile-specific roles live in `profiles/<name>/roles/`.

### base

Installs infrastructure packages (`openssh-server`, `rsync`, `socat`, `tmux`, `git`, `jq`), enables sshd, configures passwordless root SSH (empty password with `PermitEmptyPasswords`), and creates the `/isolagent` directory tree. Uses `ansible.builtin.package` for OS-agnostic package management.

### OS roles (e.g., `fedora`)

Handle OS-specific configuration. The `fedora` role runs SELinux relabeling and removes build-time NetworkManager connection profiles. Each OS role carries `vars/main.yaml` with the base image URL and hash.

### Agent roles (e.g., `agent-claude`)

Install the agent binary with a hardcoded install command. Each agent role has its own `creates` guard for idempotency.

### libvirt-bridge

Installs the `vsock-libvirt-bridge` systemd service unit. The service is disabled by default and started at session time only when `runtime.access_host_libvirt` is `true`. Automatically included when `runtime.access_host_libvirt: true` — does not need to be listed in `image.roles`.

### Profile-specific roles

Project-specific provisioning (extra packages, configuration). Stored in `profiles/<name>/roles/` and referenced by name in `image.roles`.

## Adding a New Profile

1. Create a directory under `profiles/` with a `profile.yaml`
2. Set `image.os` to the target OS (e.g., `fedora`)
3. List any agent and project-specific roles in `image.roles`
4. If needed, create profile-specific roles in `profiles/<name>/roles/`
5. Run `isolagent build <profile>`
