## ADDED Requirements

### Requirement: Install Claude Code via official install script
The `agent-claude` Ansible role SHALL install Claude Code by downloading and running the official install script from `https://claude.ai/install.sh`. The installed binary SHALL be copied to `/usr/local/bin/claude` so it is available system-wide.

#### Scenario: Fresh install
- **WHEN** the `agent-claude` role runs and `/usr/local/bin/claude` does not exist
- **THEN** the install script is downloaded and executed, and the binary is copied to `/usr/local/bin/claude` with mode 755

#### Scenario: Already installed
- **WHEN** the `agent-claude` role runs and `/usr/local/bin/claude` already exists
- **THEN** the install step is skipped (idempotent via `creates`)
