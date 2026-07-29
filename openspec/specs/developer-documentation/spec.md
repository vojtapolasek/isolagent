## ADDED Requirements

### Requirement: CLAUDE.md is a thin pointer

CLAUDE.md SHALL contain only a 2-3 sentence project description and links to relevant docs/ files. It SHALL NOT contain architecture diagrams, usage instructions, prerequisites tables, or design decisions. It SHALL include a documentation maintenance convention instructing developers to update the relevant doc in `docs/` when changing CLI flags, profile schema, setup steps, or architecture.

#### Scenario: LLM reads CLAUDE.md at session start
- **WHEN** Claude Code loads CLAUDE.md into a new conversation
- **THEN** the file is under 30 lines and contains links to docs/architecture.md, docs/testing.md, and other relevant docs

#### Scenario: Developer changes a CLI flag
- **WHEN** a developer reads CLAUDE.md
- **THEN** they find the convention "when your change affects CLI flags, profile schema, setup steps, or architecture, update the relevant doc in docs/"

### Requirement: docs/architecture.md documents system design

The project SHALL have `docs/architecture.md` that contains the system architecture diagram, design decisions with rationale, and security model description. This content SHALL be migrated from the current CLAUDE.md.

#### Scenario: Developer reads architecture overview
- **WHEN** a developer reads docs/architecture.md
- **THEN** they find the host/guest architecture diagram showing the bridge, vsock, litellm, and rsync components

#### Scenario: Developer understands design rationale
- **WHEN** a developer reads docs/architecture.md
- **THEN** they find explanations of why the libvirt API, vsock+socat, litellm proxy, rsync over SSH, and qcow2 overlays were chosen over alternatives

### Requirement: Architecture diagram
The architecture diagram SHALL show the libvirt-managed domain, default network (virbr0), vsock, litellm, and rsync components. It SHALL NOT reference a custom bridge (`br-isolagent`) or firewalld zones.

### Requirement: docs/testing.md documents test tiers

The project SHALL have `docs/testing.md` that explains the three test tiers (unit, integration, slow), the pytest commands to run each, and the prerequisites required for each tier.

#### Scenario: Developer runs unit tests
- **WHEN** a developer reads docs/testing.md
- **THEN** they find that bare `pytest` runs only unit tests and requires only Python + dependencies

#### Scenario: Developer runs integration tests
- **WHEN** a developer reads docs/testing.md
- **THEN** they find that `pytest -m integration` runs integration tests and requires `/dev/kvm`, libvirtd running, `sshpass`, `ansible-playbook`, a built image volume, and an ISO creation tool

#### Scenario: Developer runs slow tests
- **WHEN** a developer reads docs/testing.md
- **THEN** they find that `pytest -m slow` runs nested VM packet flow tests and requires nested KVM support

### Requirement: docs/host-network.md documents networking prerequisites

The project SHALL have `docs/host-network.md` that documents the libvirt default network prerequisites, URI configuration, and networking details needed for VM connectivity.

#### Scenario: Developer sets up host networking
- **WHEN** a developer reads docs/host-network.md
- **THEN** they find how to verify the libvirt default network is active and how to configure the libvirt connection URI

### Requirement: Bare pytest runs only unit tests

The `pyproject.toml` `[tool.pytest.ini_options]` section SHALL include `addopts = "-m 'not integration and not slow'"` so that running `pytest` without arguments executes only unit tests.

#### Scenario: Developer runs bare pytest
- **WHEN** a developer runs `pytest` with no arguments
- **THEN** only tests without the `integration` or `slow` markers are executed

#### Scenario: Developer opts into integration tests
- **WHEN** a developer runs `pytest -m integration`
- **THEN** tests marked with `integration` are executed (overriding the default filter)
