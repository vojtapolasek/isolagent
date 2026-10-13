# Design

## Context

`roles/agent-opencode/tasks/main.yaml` (v1) pipes `https://opencode.ai/install` into bash with `HOME=/root` and copies `$HOME/.opencode/bin/opencode` to `/usr/local/bin/opencode` (mode 755, `creates:`-guarded). That endpoint serves the v1 line (anomalyco/opencode GitHub releases; latest `v1.19.0`).

The official v2 install script (`https://opencode.ai/v2/install`) was inspected: it resolves the latest release from `https://opencode.ai/update/api/latest/cli/npm`, downloads a platform tarball from the npm registry, and installs the main binary as `$HOME/.opencode/bin/opencode` (plus a legacy `opencode2` shim pointing at it). It works non-interactively and supports `--version <x>` pinning. The existing role's copy-to-`/usr/local/bin` pattern therefore transfers unchanged; only the script URL differs.

The v2 binary (verified against `v2.0.28`) supports the `--auto` flag — "auto-approve permissions that are not explicitly denied" — so consuming profiles need no v2-specific launch changes.

## Goals / Non-Goals

**Goals:**
- A global `agent-opencode-v2` role that installs the latest OpenCode v2 on every fresh image build.
- The role is self-contained and reusable by any profile (shipped or not) via `image.roles`.

**Non-Goals:**
- A shipped v2 quickstart profile (users consume the role from their own non-shipped profiles).
- Replacing or modifying `agent-opencode` / `opencode-quickstart`.
- Version pinning support in the role (always latest; the script's `--version` flag is a possible future role variable).
- Changes to `isolagent` source, schema, or `.gitignore`.

## Decisions

- **New global role instead of modifying `agent-opencode`** — profiles opt in via `image.roles`, so a second role delivers both product lines with no schema change and leaves the `agent-opencode-role` spec untouched. Alternative (change the existing role to v2) breaks every existing v1 profile. Name `agent-opencode-v2` follows the `agent-<name>` convention; role resolution finds it in the global `roles/` directory like other agent roles.
- **Role task body mirrors `agent-opencode` exactly**, with only the URL swapped to `https://opencode.ai/v2/install`:

  ```yaml
  - name: Install Opencode v2
    ansible.builtin.shell:
      cmd: "curl -fsSL https://opencode.ai/v2/install | bash && cp $HOME/.opencode/bin/opencode /usr/local/bin/opencode && chmod 755 /usr/local/bin/opencode"
    environment:
      HOME: /root
    args:
      creates: /usr/local/bin/opencode
  ```
  The `opencode2` legacy shim created by the script is deliberately not copied — the agent command is `opencode`.
- **Both roles install to the same path (`/usr/local/bin/opencode`)** — a profile listing both roles gets first-role-wins (the second role's `creates:` guard skips). Mixing v1 and v2 roles in one profile is meaningless, so no conflict detection is added.

## Risks / Trade-offs

- [`creates:` guard means only a fresh image (`isolagent build --force`) upgrades a previously installed binary] → Same as the v1 role; images are disposable.
- [v2 install script depends on `opencode.ai/update/api/latest/cli/npm` and the npm registry] → Same supply chain opencode documents for v2; failures are loud build errors, never a silent wrong version.
- [`--auto` is undocumented on the online v2 CLI page, so a future v2 release could rename or drop it] → Verified present in `v2.0.28`; consuming profiles are out of this change's scope, and an integration build catches regressions.
