## Why

The session runtime (`session.py`) disables git hooks inside the VM by setting `core.hooksPath /dev/null` when output mode is `patch`. This couples the runtime to a git-specific concern that belongs to individual profile Ansible roles. This was a relic from the project's early wild development phase and should be removed so the runtime stays git-hooks-agnostic.

## What Changes

- Remove the `_ssh_run` call that sets `git config core.hooksPath /dev/null` from the patch-mode setup block in `session.py` (lines 467-470).
- Keep the `initial_head` capture (`git rev-parse HEAD`) which is core patch-mode mechanics.
- No new code added — profiles that need hooks disabled should handle it in their own Ansible roles.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None — this is a pure removal of runtime behavior that was never the runtime's responsibility. No spec-level behavior changes. `skip_specs: true` is set in `.openspec.yaml`.

## Impact

- **Code**: `isolagent/session.py` — 4 lines removed from `init()` method.
- **Profiles**: Any profile that relied on the runtime disabling hooks will now need to add a git config task to its own Ansible role. No existing profiles in-tree do this.
- **Tests**: No test changes needed — no tests covered this behavior.
