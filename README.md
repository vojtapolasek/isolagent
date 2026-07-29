# isolagent

> **Status:** Under heavy development. But I will try not to introduce breaking changes.

Run fully autonomous LLM agents in isolated sandbox without being afraid that they will break your host.

Configurable QEMU sandbox with KVM-level hardware isolation. Profiles define the base image, agent, runtime resources, and project to sync in.

## Quick Start

```shell
# Install the CLI
pip install -e .

# Edit profiles/opencode-quickstart/profile.yaml — set project.workdir to your project path

# Build the VM image (downloads base image, runs Ansible provisioner)
isolagent build opencode-quickstart

# Launch a sandbox session
isolagent run opencode-quickstart --output-mode none

# Inside the sandbox, type /connect in opencode to configure your LLM provider
```

## Prerequisites

- libvirtd and QEMU with KVM support
- Ansible
- rsync
- sshpass
- genisoimage or xorrisofs
- socat (only needed if `runtime.access_host_libvirt` is enabled)
- litellm (optional, for API key isolation) — see [litellm Proxy](docs/litellm.md)

KVM must be available (`/dev/kvm`). Enable hardware virtualization in BIOS if missing. Your user must be in the `libvirt` group (`sudo usermod -aG libvirt $USER`).

## Documentation

- [Architecture](docs/architecture.md) — system design, security model, design decisions
- [Host Network Setup](docs/host-network.md) — libvirt default network, prerequisites
- [litellm Proxy](docs/litellm.md) — API key isolation, presets, systemd service
- [Profiles](docs/profiles.md) — profile authoring, field reference, examples
- [Image Building](docs/image-building.md) — libvirt-based image building, playbook customization
- [Sessions](docs/sessions.md) — session lifecycle, output modes
- [Testing](docs/testing.md) — test tiers, commands, prerequisites

## Contributing

Issues and pull requests are welcome.

I strongly encourage you to use the [Openspec](https://openspec.dev/) as separate commits in PRs so that we track the evolution of the project.

## License

[MIT](LICENSE)
