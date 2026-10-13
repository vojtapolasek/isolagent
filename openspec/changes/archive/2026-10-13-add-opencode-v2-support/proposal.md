# Proposal

## Why

The global `agent-opencode` role installs OpenCode v1 (`https://opencode.ai/install`, currently the v1.x line), but OpenCode v2 is a separate product line with its own official install script (`https://opencode.ai/v2/install`). Users need a global role that installs the latest OpenCode v2 so it can be reused across profiles, without losing the existing v1 role.

## What Changes

- Add a new global Ansible role `agent-opencode-v2/` that installs the latest OpenCode v2 via the official v2 install script and makes the binary available system-wide at `/usr/local/bin/opencode`, mirroring the `agent-opencode` structure.
- Keep `agent-opencode` (v1) unchanged; profiles opt into v2 by listing `agent-opencode-v2`.
- Document the new role in `docs/architecture.md`.

## Capabilities

### New Capabilities
- `agent-opencode-v2-role`: installation of the latest OpenCode v2 as a global Ansible role, reusable by any profile.

### Modified Capabilities
<!-- none — agent-opencode-role keeps its current v1 behavior -->

## Impact

- New files: `roles/agent-opencode-v2/tasks/main.yaml`.
- Docs: `docs/architecture.md` (roles tree).
- No changes to `isolagent` source, CLI behavior, `profile_schema.json`, shipped profiles, or `.gitignore` (no new shipped profile; the role is consumed by non-shipped user profiles via `image.roles`).
- Out of scope: a v2 quickstart profile; switching any existing profile to v2.
