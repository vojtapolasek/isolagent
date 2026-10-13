# Tasks

## 1. Global role

- [x] 1.1 Create `roles/agent-opencode-v2/tasks/main.yaml` mirroring `roles/agent-opencode/tasks/main.yaml`, but fetching `https://opencode.ai/v2/install` and copying `$HOME/.opencode/bin/opencode` to `/usr/local/bin/opencode` (chmod 755, `HOME=/root`, guarded by `creates: /usr/local/bin/opencode`).

## 2. Documentation

- [x] 2.1 Update the roles tree in `docs/architecture.md` to list `agent-opencode-v2/`.

## 3. Verification

- [x] 3.1 Lint the new role (`ansible-lint roles/agent-opencode-v2` or `ansible-playbook --syntax-check` on a generated playbook).
- [x] 3.2 Run `python -m pytest` and confirm the unit tier still passes (no code changes; sanity check).
- [x] 3.3 Integration (requires KVM/libvirt): with a scratch profile (e.g. in `/tmp`, `image.roles: [agent-opencode-v2]`, `agent.command: "opencode --auto"`) run `isolagent build <name> --profiles-dir /tmp/...`, then `isolagent run ... --shell` and confirm `opencode --version` reports `2.x` and `opencode --auto` starts unattended.
