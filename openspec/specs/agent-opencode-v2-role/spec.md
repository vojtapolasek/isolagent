# agent-opencode-v2-role Specification

## Purpose

Define the global agent-opencode-v2 Ansible role -- installation of the latest OpenCode v2 release inside the sandbox image, made available system-wide.

## Requirements

### Requirement: Install OpenCode v2 via official v2 install script
The `agent-opencode-v2` Ansible role SHALL install OpenCode v2 by downloading and running the official install script from `https://opencode.ai/v2/install`. The installed binary SHALL be copied to `/usr/local/bin/opencode` so it is available system-wide with mode 755.

#### Scenario: Fresh install
- **WHEN** the `agent-opencode-v2` role runs and `/usr/local/bin/opencode` does not exist
- **THEN** the v2 install script is downloaded and executed, and the binary is copied to `/usr/local/bin/opencode` with mode 755

#### Scenario: Already installed
- **WHEN** the `agent-opencode-v2` role runs and `/usr/local/bin/opencode` already exists
- **THEN** the install step is skipped (idempotent via `creates`)

### Requirement: Role targets the v2 product line
The `agent-opencode-v2` role SHALL fetch from the v2 install endpoint so a fresh install yields an OpenCode v2 (`2.x`) binary, and SHALL install the latest available v2 release by default.

#### Scenario: Latest v2 release installed
- **WHEN** the role installs OpenCode on a fresh image
- **THEN** `opencode --version` in the guest reports a `2.x` version

#### Scenario: v1 role unaffected
- **WHEN** a user compares `roles/agent-opencode-v2/` with `roles/agent-opencode/`
- **THEN** both roles exist independently and reference different install URLs
