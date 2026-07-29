## Requirements

### Requirement: Install OpenCode via official install script
The `agent-opencode` Ansible role SHALL install OpenCode by downloading and running the official install script from `https://opencode.ai/install`. The installed binary SHALL be copied to `/usr/local/bin/opencode` so it is available system-wide.

#### Scenario: Fresh install
- **WHEN** the `agent-opencode` role runs and `/usr/local/bin/opencode` does not exist
- **THEN** the install script is downloaded and executed, and the binary is copied to `/usr/local/bin/opencode` with mode 755

#### Scenario: Already installed
- **WHEN** the `agent-opencode` role runs and `/usr/local/bin/opencode` already exists
- **THEN** the install step is skipped (idempotent via `creates`)
