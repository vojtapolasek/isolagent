## Context

See proposal.md for motivation. The current code in `session.py` `init()` method (lines 463-470):

```python
if self.output_mode == "patch":
    self.initial_head = self._ssh_exec(
        "cd /isolagent/project && git rev-parse HEAD"
    )
    self._ssh_run(
        "cd /isolagent/project && "
        "git config core.hooksPath /dev/null"
    )
```

The `_ssh_run` call (lines 467-470) is the only place in the codebase that touches git hooks. The `initial_head` capture (lines 464-466) is unrelated patch-mode machinery that must stay.

## Goals / Non-Goals

**Goals:**
- Remove the git hooks disabling code from the session runtime.
- Keep the patch-mode `initial_head` capture intact.

**Non-Goals:**
- Adding git hook management to any existing profile Ansible role — that's a profile author's decision.
- Modifying tests — no tests cover this behavior.

## Decisions

**Delete only the `_ssh_run` call, keep the surrounding `if` block.**

The `if self.output_mode == "patch"` guard and the `initial_head` assignment inside it are core patch-mode mechanics used by `_patch_format_cmd()`. Only the `_ssh_run` call that sets `core.hooksPath` is removed.

Alternative considered: removing the entire `if` block and lazily capturing `initial_head` inside `_patch_format_cmd`. Rejected — it would change the timing of HEAD capture relative to agent execution, which is a separate concern.

## Risks / Trade-offs

- **[Profile breakage]** → A profile that depends on the runtime disabling hooks will see hook failures after this change. Mitigation: no in-tree profiles rely on this. Out-of-tree profiles would need to add a `git config --global core.hooksPath /dev/null` task to their Ansible role.
