# AGENTS.md

Configurable QEMU sandbox for running fully autonomous LLM agents with KVM-level isolation. Profiles define images, agents, resources, and projects. Install with `pip install -e .`, run `isolagent build <profile>`, then `isolagent run <profile> --output-mode patch`.

## Documentation

- [Architecture](docs/architecture.md) — system design, security model, design decisions
- [Host Network Setup](docs/host-network.md) — libvirt default network, prerequisites
- [litellm Proxy](docs/litellm.md) — API key isolation, presets, systemd service
- [Profiles](docs/profiles.md) — profile authoring, field reference, examples
- [Image Building](docs/image-building.md) — libvirt-based image building, playbook customization
- [Sessions](docs/sessions.md) — session lifecycle, output modes
- [Testing](docs/testing.md) — test tiers, commands, prerequisites

## Documentation Maintenance

When your change affects CLI flags, profile schema fields, setup steps, or architecture, update the relevant doc in `docs/`.

## Profile Schema

When changing the profile schema (`profile_schema.json`), update the reference profile (`profiles/reference/profile.yaml`) to reflect the change. The reference profile must validate against the schema.

## Build and Test

```shell
pip install -e ".[dev]"
python -m pytest
```

Integration tests require libvirt, Ansible, and KVM. See [Testing](docs/testing.md) for details.
