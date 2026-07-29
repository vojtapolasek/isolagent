# Sessions

`isolagent run <profile>` launches an ephemeral QEMU VM, syncs the project in, runs the agent, extracts output, and cleans up. Each session starts from a clean qcow2 overlay on the immutable base image.

## Running a Session

```shell
isolagent run opencode-quickstart --output-mode patch
```

`--output-mode` is required unless `--shell` is used. The three modes are: `patch` (extract git commits as a patch file), `sync` (rsync all changes back), and `none` (discard changes).

### Shell Mode

Drop into an interactive SSH shell instead of running the agent:

```shell
isolagent run opencode-quickstart --shell
```

### Runtime Overrides

Override profile defaults from the command line:

```shell
isolagent run opencode-quickstart --output-mode patch --memory 8G --cpus 8
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--memory` | string | `"4G"` | Guest memory (e.g., `8G`). Overrides `runtime.memory` |
| `--cpus` | integer | `4` | Guest vCPUs. Overrides `runtime.cpus` |
| `--output-dir` | string | same as `project.workdir` | Directory for patch/sync output (required for sync) |
| `--overwrite` | flag | off | Allow sync into a non-empty output directory |

## Session Lifecycle

### Preflight

Validates that all prerequisites are met before starting the VM:

- libvirtd is running and accessible
- libvirt default network exists and is active
- libvirt storage pool exists
- Built image volume exists in the pool (run `isolagent build <profile>` first)
- An ISO creation tool is available (for cloud-init ISO generation)
- Extra sync paths have no basename collisions
- Output directory exists and is writable (when `--output-dir` is specified)
- Output directory is empty for sync mode (unless `--overwrite` is used)

If any check fails, the error message tells you which setup step to run.

### VM Boot

1. A qcow2 overlay volume is created on top of the base image volume
2. A cloud-init ISO is generated with DHCP network configuration
3. A libvirt domain is defined and started with KVM, virbr0 networking, and a vsock device
4. The session waits for libvirt's DHCP to assign an IP, then queries the lease to discover the guest IP
5. If `runtime.access_host_libvirt` is `true`, a socat process bridges VSOCK to the host libvirt socket (using flock to prevent duplicate processes)

### SSH Wait

The session waits up to 60 seconds for SSH to become available on the guest, polling once per second. If SSH is not available after 60 seconds, the session raises an error.

### Project Sync

The project directory (`project.workdir`) is rsynced into `/isolagent/project/` on the guest. Extra sync directories are rsynced into `/isolagent/<dirname>/`. Guest files from the profile's `guest-files/` directory are then deployed via SCP. The directory tree mirrors the guest filesystem: a file at `guest-files/root/.claude.json` is copied to `/root/.claude.json` on the guest. Prompt files are handled the same way -- place them at the desired guest path inside `guest-files/` (e.g., `guest-files/isolagent/project/CLAUDE.md`).

### Agent Launch

In agent mode, the agent command is launched inside a tmux session named `isolagent`. Environment variables from `agent.env` are injected inline using `env KEY=VALUE` syntax before the agent command. The host terminal attaches to this tmux session. If the connection drops, the session reconnects automatically (up to 10 consecutive failures before giving up).

In shell mode, an interactive SSH session is opened directly.

### Output Extraction

After the agent exits (or the shell session ends), output is extracted according to the `--output-mode` flag: `patch` generates a git format-patch, `sync` rsyncs the project back, and `none` discards all changes.

### Teardown

Teardown runs regardless of whether the session succeeded or failed:

1. Output extraction (if VM is reachable)
2. libvirt domain destroyed (VM stopped)
3. qcow2 overlay volume deleted from storage pool
4. socat shared lock released; socat process stopped if no other sessions hold a lock
5. Cloud-init directory, ISO, and console log deleted

## Output Modes

### patch

Extracts the agent's git commits as a patch file. Use when you want to review changes before applying them.

```shell
isolagent run opencode-quickstart --output-mode patch
```

At session start, the current `HEAD` is recorded. At session end, `git format-patch` generates a patch containing all commits made by the agent. The patch is saved to `<workdir>/isolagent-<timestamp>.patch`.

Apply the patch:

```shell
cd ~/my-project
git am isolagent-2026-07-21-143052.patch
```

Uncommitted changes in the guest are warned about but not included in the patch.

### sync

Mirrors the entire `/isolagent/project/` directory from the guest to the host using rsync with `--delete`. This is a full mirror: files deleted by the agent in the guest are also removed from the output directory. `--output-dir` is required for sync mode.

```shell
isolagent run opencode-quickstart --output-mode sync --output-dir ~/output/example
```

The output directory must exist and be empty. To sync into a directory that already contains files (e.g., repeated runs to the same directory), pass `--overwrite`:

```shell
isolagent run opencode-quickstart --output-mode sync --output-dir ~/output/example --overwrite
```

To sync directly back into your working copy (replacing it with the guest's version):

```shell
isolagent run opencode-quickstart --output-mode sync --output-dir ~/my-project --overwrite
```

### none

Discards all changes. Use for testing or exploratory sessions.

```shell
isolagent run opencode-quickstart --output-mode none
```

## Listing Active Sessions

```shell
isolagent list
```

Shows domain name, profile name, guest IP, and domain state for each active session. The listing queries libvirt for domains tagged with the sandbox marker.
