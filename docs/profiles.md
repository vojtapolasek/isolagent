# Profiles

A profile is a directory that defines everything needed to build and run a sandbox: which OS to use, which roles to provision, how to launch the agent, what runtime resources to allocate, and which project to sync in. Each profile lives in `profiles/<name>/` and contains a `profile.yaml`, an optional `guest-files/` subdirectory, and an optional `roles/` subdirectory for profile-specific Ansible roles.

## Directory Layout

```
profiles/
  my-sandbox/
    profile.yaml              # required — profile configuration
    guest-files/              # optional — files deployed into the guest
      root/
        .claude.json
        .ssh/
          config
    roles/                    # optional — profile-specific Ansible roles
      my-sandbox/
        tasks/main.yaml
```

## Quickstart Profile

The `opencode-quickstart` profile is the recommended starting point. It uses [opencode](https://opencode.ai) with auto-approve permissions and requires no litellm proxy or environment variables — configure your provider interactively with `/connect` after the agent starts.

```yaml
# profiles/opencode-quickstart/profile.yaml
name: opencode-quickstart

image:
  os: fedora
  roles:
    - agent-opencode

agent:
  command: "opencode --auto"

project:
  workdir: ~/my-project   # ← change this to your project path
```

## Minimal Profile

A valid profile requires four sections: `name`, `image`, `agent`, and `project`. All `runtime` fields have defaults.

```yaml
# profiles/my-sandbox/profile.yaml
name: my-sandbox

image:
  os: fedora

agent:
  command: "claude --dangerously-skip-permissions"

project:
  workdir: "~/my-project"
```

## Full Profile

See `profiles/reference/profile.yaml` for a complete profile showing every optional field with comments. It serves as the canonical reference for profile authoring.

## Field Reference

### image

Configuration for the VM image built by `isolagent build`.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `os` | string | yes | — | OS role name (e.g., `fedora`). Determines the base cloud image and OS-specific provisioning |
| `roles` | array of strings | no | `[]` | Profile-specific Ansible roles to apply during image build. Resolved from the profile's `roles/` directory first, then the global `roles/` directory |

The base image URL and SHA-256 hash are defined in the OS role's `vars/main.yaml`, not in the profile.

### agent

Configuration for the AI agent running inside the sandbox.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `command` | string | yes | — | Shell command to launch the agent at session start |
| `env` | object | no | `{}` | Environment variables injected inline with the agent command using `env KEY=VALUE` syntax. Values must be strings |

Agent installation is handled by agent roles (e.g., `agent-claude`) listed in `image.roles`.

### runtime

Resource allocation and runtime behavior for the QEMU VM.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `access_host_libvirt` | boolean | no | `false` | Enable the vsock-libvirt bridge for accessing host libvirt VMs |
| `libvirt_uri` | string | no | `qemu:///system` | Libvirt connection URI override. Can also be set via `ISOLAGENT_LIBVIRT_URI` env var |
| `memory` | string | no | `"4G"` | Guest memory allocation (e.g., `"2G"`, `"8G"`) |
| `cpus` | integer | no | `4` | Guest vCPU count. Minimum: 1 |
| `disk` | string | no | `"20G"` | Session disk size: overlay virtual size and usable root filesystem. Positive integer with unit suffix `M`, `G`, or `T` (e.g., `"20G"`, `"512M"`, `"1T"`). Must be at least the base image's virtual size |

### project

Configuration for the project synced into the guest.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `workdir` | string | yes | — | Path to the project directory on the host. Supports `~` expansion. Synced to `/isolagent/project/` in the guest |
| `extra_syncs` | array of strings | no | `[]` | Additional directories to sync into the guest. Each is synced to `/isolagent/<dirname>/`. Basenames must not collide with each other or with `project` |

## Guest Files

Each profile directory may contain an optional `guest-files/` subdirectory. Files placed here are deployed into the guest VM at session time via SCP (they are not baked into the image at build time). The directory tree mirrors absolute guest paths: a file at `guest-files/root/.claude.json` is copied to `/root/.claude.json` inside the guest.

```
profiles/reference/
  profile.yaml
  guest-files/
    root/
      .claude.json                  -> /root/.claude.json
      .claude/
        settings.json               -> /root/.claude/settings.json
        CLAUDE.md                   -> /root/.claude/CLAUDE.md
      .ssh/
        config                      -> /root/.ssh/config
```

If the `guest-files/` directory is absent or empty, no extra files are deployed.

## Path Expansion

Paths in `project.workdir` and `project.extra_syncs` support `~` (home directory) and `$VAR` (environment variable) expansion.

## Validation

Profiles are validated against a JSON Schema (`isolagent/profile_schema.json`) at load time. Invalid profiles produce an error message identifying the failing field and constraint.
