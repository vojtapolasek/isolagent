## ADDED Requirements

### Requirement: README.md exists as project front door

The project SHALL have a `README.md` at the repo root that serves as the entry point for new users. It SHALL open with the tagline "Run fully autonomous LLM agents in isolated sandbox without being afraid that they will break your host." It SHALL contain a quick start section with the minimal sequence of commands to go from zero to a running sandbox using the `opencode-quickstart` profile, a link to `docs/` for detailed documentation, and a summary list of prerequisites (package names only, not install instructions). All examples SHALL use `opencode-quickstart` as the profile name and `isolagent` as the CLI command. No specific use-case project SHALL be mentioned.

#### Scenario: New user reads README
- **WHEN** a user opens the repository for the first time
- **THEN** README.md provides a self-contained quick start that covers: install Python dependencies, run `isolagent build opencode-quickstart`, run `isolagent run opencode-quickstart --output-mode patch`

#### Scenario: Quick start references only the isolagent CLI
- **WHEN** README.md lists setup and usage commands
- **THEN** all commands use the `isolagent` CLI (not `sandbox` or legacy shell scripts)

#### Scenario: No use-case-specific references
- **WHEN** a user reads README.md
- **THEN** no specific project names, company names, or domain-specific tooling are mentioned

### Requirement: docs/profiles.md documents profile authoring

The project SHALL have `docs/profiles.md` that explains how to write a profile. It SHALL cover all four profile sections (`image`, `agent`, `runtime`, `project`), state the type, default, and constraints of every field, and reference the `reference` profile as the canonical full example showing all schema fields.

#### Scenario: User creates a new profile
- **WHEN** a user reads docs/profiles.md
- **THEN** they find a minimal profile YAML example that is valid and complete (all required fields, no optional fields)

#### Scenario: User discovers optional fields
- **WHEN** a user reads docs/profiles.md
- **THEN** they are directed to `profiles/reference/profile.yaml` as the reference showing every optional field

### Requirement: docs/litellm.md documents litellm proxy setup

The project SHALL have `docs/litellm.md` that explains what litellm does in this project (API key isolation and model routing), presents it as optional, and provides setup instructions for users who choose to use it. The document SHALL open by stating that litellm is not required — agents like opencode can manage their own provider credentials — but is recommended when API keys must not enter the sandbox.

#### Scenario: User sets up litellm for the first time
- **WHEN** a user reads docs/litellm.md
- **THEN** they find step-by-step instructions from installing litellm through verifying the health endpoint

#### Scenario: User finds example configuration
- **WHEN** a user reads docs/litellm.md
- **THEN** they find a fenced YAML block with a litellm config example using placeholder values (e.g. `YOUR_PROJECT_ID`)

#### Scenario: User understands litellm is optional
- **WHEN** a user reads the opening section of docs/litellm.md
- **THEN** they find a clear statement that litellm is optional and that agents can manage provider credentials directly

#### Scenario: User understands when litellm is recommended
- **WHEN** a user reads docs/litellm.md
- **THEN** they find an explanation of when to use litellm: API key isolation (sandbox never sees real keys) and model routing (multiple backends without guest changes)

### Requirement: docs/image-building.md documents the build pipeline

The project SHALL have `docs/image-building.md` that uses `isolagent` as the CLI name and `opencode-quickstart` as the profile name in all examples.

#### Scenario: User builds an image for the first time
- **WHEN** a user reads docs/image-building.md
- **THEN** they find the `isolagent build opencode-quickstart` command and its prerequisites

### Requirement: docs/sessions.md documents the sandbox run lifecycle

The project SHALL have `docs/sessions.md` that uses `isolagent` as the CLI name and `opencode-quickstart` as the profile name in all examples. It SHALL NOT reference any specific use-case project.

#### Scenario: User reads session docs
- **WHEN** a user reads docs/sessions.md
- **THEN** all CLI examples use `isolagent run opencode-quickstart`, `isolagent build opencode-quickstart`, etc.

### Requirement: docs/architecture.md documents system design generically

The project SHALL have `docs/architecture.md` that describes the system architecture without referencing any specific use-case project. litellm SHALL be described as an optional component for API key isolation and model routing. The security model section SHALL present two approaches: (1) litellm proxy for key isolation, and (2) agent-managed credentials where the agent handles provider auth directly.

#### Scenario: Architecture presents litellm as optional
- **WHEN** a user reads the system overview in docs/architecture.md
- **THEN** litellm is shown with an "(optional)" annotation and the text explains it is needed only when API key isolation is required

#### Scenario: Security model covers both approaches
- **WHEN** a user reads the API Key Isolation section in docs/architecture.md
- **THEN** they find both the litellm approach (keys never enter the sandbox) and the agent-managed approach (agent handles credentials directly, simpler but keys exist inside the sandbox)

#### Scenario: Architecture describes libvirt bridge generically
- **WHEN** a user reads docs/architecture.md
- **THEN** the libvirt bridge is described as enabling "workloads that manage VMs on the host" without naming any specific tool or project

### Requirement: litellm-presets/README.md is removed

`litellm-presets/README.md` SHALL be deleted. Documentation for litellm lives in `docs/litellm.md`.

#### Scenario: litellm-presets directory contains only preset files
- **WHEN** a user lists files in litellm-presets/
- **THEN** only YAML preset files are present (no README.md)
