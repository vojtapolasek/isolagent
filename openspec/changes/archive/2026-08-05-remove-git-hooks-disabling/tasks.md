## 1. Remove git hooks disabling

- [x] 1.1 Remove the `_ssh_run` call that sets `core.hooksPath /dev/null` from `isolagent/session.py` (lines 467-470), keeping the `initial_head` capture intact.

## 2. Verify

- [x] 2.1 Run the existing test suite to confirm nothing breaks.
