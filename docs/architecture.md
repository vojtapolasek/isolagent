# Architecture

Configurable QEMU sandbox for running AI coding agents with KVM-level isolation. The host provides networking, API proxying, and hypervisor access; the guest runs the agent in an ephemeral VM with no persistent state.

## System Overview

```
Host (Fedora / Arch Linux)
├── libvirtd (qemu:///system or qemu:///session)
│   ├── Default network (virbr0, 192.168.122.0/24, DHCP + NAT)
│   └── Storage pool (VM images as libvirt volumes)
├── litellm (optional, systemd --user service, 0.0.0.0:4000)
│   └── Credential injection (sandbox never sees real API keys)
├── roles/                    ← global Ansible roles
│   ├── base/                 ← sandbox infrastructure (SSH, rsync, socat)
│   ├── fedora/               ← OS-specific config + base image metadata
│   ├── agent-claude/         ← Claude Code installation
│   ├── agent-opencode/       ← OpenCode v1 installation
│   ├── agent-opencode-v2/    ← OpenCode v2 installation
│   ├── agent-test/           ← test agent installation
│   └── libvirt-bridge/       ← vsock-to-TCP bridge service
├── profiles/<name>/
│   ├── profile.yaml          ← profile definition
│   ├── guest-files/          ← optional, mirrors guest filesystem
│   └── roles/                ← optional, profile-specific Ansible roles
├── isolagent build <profile>
│   └── libvirt-based build + generated Ansible playbook → libvirt volume
└── isolagent run <profile>
    ├── qcow2 overlay volume on base image (ephemeral, deleted on exit)
    ├── libvirt domain: virbr0 networking (DHCP), vhost-vsock-pci
    ├── Host socat: VSOCK → libvirt Unix socket (if libvirt access enabled)
    ├── SCP guest-files into VM, rsync project in, run agent, extract output
    ├── agent.env injected inline with the agent command
    └── Cleanup on exit (domain destroy, overlay deletion, socat stop)

Guest (prebaked cloud image)
├── root user, SSH with passwordless auth (empty password, no keys)
├── socat systemd unit: TCP :16509 → VSOCK CID 2:16509
├── ANTHROPIC_BASE_URL → http://192.168.122.1:4000 (litellm on host, if used)
├── python3-libvirt → qemu+tcp://127.0.0.1:16509/system
└── Project-specific deps installed via profile roles
```

## Role Layering

The builder generates Ansible playbooks dynamically from the profile. Roles are applied in this order:

1. **base** — always first, implicit. Sandbox infrastructure only.
2. **OS role** — implicit, from `image.os`. OS-specific config and base image metadata.
3. **libvirt-bridge** — implicit when `runtime.access_host_libvirt: true`.
4. **Profile roles** — from `image.roles`. Agent installation and project-specific provisioning.

Role resolution searches the profile's `roles/` directory first, then the global `roles/` directory. Profile-local roles take precedence over global roles with the same name.

## Security Model

### API Key Management

There are two approaches to handling API credentials in the sandbox:

**Agent-managed credentials** — The agent handles provider authentication directly inside the guest. For example, opencode's `/connect` command lets users configure any provider interactively. This is the simplest setup and requires no host-side infrastructure beyond the sandbox itself. The trade-off is that API keys exist inside the guest and could be exfiltrated by a compromised agent.

**litellm proxy (recommended for sensitive keys)** — A litellm proxy runs on the host and injects credentials into requests. Inside the guest, `ANTHROPIC_API_KEY` is set to `"unused"` and `ANTHROPIC_BASE_URL` points to the libvirt default network gateway (`http://192.168.122.1:4000`). A compromised agent cannot exfiltrate credentials because they do not exist in the guest. See [litellm Proxy](litellm.md) for setup instructions.

`ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL` variable names can be changed to something else what is honored by the agent.

### Filesystem Isolation

Project files are copied into the guest via rsync, not mounted. The agent works on a copy. A compromised agent cannot modify host files. Output extraction (patch or sync) happens only at session end, and the host controls whether to apply changes.

### Network Isolation

The guest attaches to libvirt's default network (virbr0), which provides NAT and DHCP. libvirt's nftables rules isolate VM traffic. Internet access is provided via NAT masquerade. The host system is not directly reachable from the guest except when explicitly bridged via VSOCK for libvirt API access.

### Ephemeral State

Each session uses a qcow2 overlay volume on an immutable base image volume. The overlay is deleted on exit. No guest state persists between sessions.

## Design Decisions

### libvirt API

The libvirt Python API provides a high-level interface for VM lifecycle management. libvirt handles DHCP allocation, VSOCK CID assignment, domain XML generation, and network isolation. KVM provides hardware-level isolation. Memory balloon returns unused pages to the host, so a 4G guest does not permanently consume 4G of host RAM.

### virtio-vsock + socat

The guest needs to reach libvirtd on the host for workloads that manage VMs on the host. Exposing libvirtd on TCP would be a security risk. Instead, a virtio-vsock device provides a host-guest communication channel. socat bridges VSOCK to the libvirt Unix socket on the host side, and TCP to VSOCK on the guest side. The guest connects to `qemu+tcp://127.0.0.1:16509/system`, which is transparently bridged to the host's libvirt.

### litellm Proxy (Optional)

Running litellm on the host keeps API credentials out of the sandbox entirely. The proxy also enables model routing — different profiles can target different backends (Vertex AI, local models via llama-swap) without changing the guest configuration. litellm is not required when the agent manages its own provider credentials (e.g., opencode's `/connect`). Install litellm on the host, configure a preset, and run it as a systemd user service on port 4000. Full setup instructions are in [docs/litellm.md](litellm.md).

### Profile Directories

Each profile is a directory under `profiles/<name>/` containing a `profile.yaml`, an optional `guest-files/` subdirectory, and an optional `roles/` subdirectory. The `guest-files/` tree mirrors the guest filesystem — for example, `profiles/myprofile/guest-files/root/.bashrc` is deployed to `/root/.bashrc` in the guest. Profile-specific roles keep provisioning logic co-located with the profile that needs it.

Guest files are deployed at session time via SCP, not baked into the image. This means changes to guest files take effect on the next `isolagent run` without rebuilding the image.

### Dynamic Playbook Generation

The builder generates Ansible playbooks at build time from the profile's role list rather than maintaining static playbook files. This eliminates duplication and makes the profile the single source of truth for what gets provisioned.

### agent.env Injection

Environment variables defined in `agent.env` are injected inline with the agent command at session time, not written to a file in the guest. This avoids persisting secrets on the guest filesystem.

### rsync Over SSH

Project content is copied in, not mounted. This ensures a compromised agent cannot damage host files. rsync is fast and  handles large repos well.

### qcow2 Overlays

Each session creates a copy-on-write overlay volume on the immutable base image volume. The overlay captures all guest writes. Deleting the overlay on exit gives a clean slate. The base image is never modified after build.
