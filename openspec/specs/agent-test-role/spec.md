## ADDED Requirements

### Requirement: Install agent-test script via Ansible role
The `agent-test` Ansible role SHALL copy `agent-test.sh` to `/usr/local/bin/agent-test` with mode `0755` so it is available as the agent command in test profiles.

#### Scenario: Role execution
- **WHEN** the `agent-test` role runs during image provisioning
- **THEN** the script is installed at `/usr/local/bin/agent-test` and is executable

### Requirement: Validate environment variable injection
The agent-test script SHALL verify that profile-defined environment variables are correctly injected into the guest.

#### Scenario: Variable with a value
- **GIVEN** the profile sets `SANDBOX_TEST_VAR: "expected-value"`
- **WHEN** the script runs inside the guest
- **THEN** the `env_var_set` check passes

#### Scenario: Empty variable
- **GIVEN** the profile sets `SANDBOX_TEST_EMPTY: ""`
- **WHEN** the script runs inside the guest
- **THEN** the `env_var_empty` check passes (the variable is set but empty)

### Requirement: Validate project sync
The agent-test script SHALL verify that the host project directory is synced into the guest at `/isolagent/project`.

#### Scenario: Project directory and file present
- **WHEN** the script runs inside the guest
- **THEN** `/isolagent/project` exists as a directory and `/isolagent/project/README.md` exists as a file

### Requirement: Validate extra syncs
The agent-test script SHALL verify that extra sync entries from the profile are mounted into the guest.

#### Scenario: Extra sync directory and content
- **WHEN** the profile defines an extra sync targeting `/isolagent/extra-test`
- **THEN** `/isolagent/extra-test` exists and `/isolagent/extra-test/extra-marker.txt` contains `extra-sync-ok`

### Requirement: Validate guest files
The agent-test script SHALL verify that profile-defined guest files are written into the guest filesystem.

#### Scenario: Marker file present
- **WHEN** the profile defines a guest file at `~/.test-marker` with content containing `isolagent-test-ok`
- **THEN** the `guest_file_marker` check passes

### Requirement: Produce file modifications for output extraction
The agent-test script SHALL modify a tracked file in `/isolagent/project` and commit the change so that session output extraction (patch/diff modes) can capture the modification.

#### Scenario: Git commit in project directory
- **WHEN** the script runs
- **THEN** it appends to `README.md`, stages all changes, and commits with message `agent: test modification`

### Requirement: Write structured results to JSON
The agent-test script SHALL write a JSON results file to `/tmp/test-results.json` summarizing all checks.

#### Scenario: Results file format
- **WHEN** all checks complete
- **THEN** `/tmp/test-results.json` contains `{"passed": N, "failed": M, "all_passed": bool, "checks": [...]}`

#### Scenario: Any check fails
- **WHEN** one or more checks fail
- **THEN** the script exits with code 1 and prints the results to stderr

#### Scenario: All checks pass
- **WHEN** all checks pass
- **THEN** the script exits with code 0 and prints `ALL CHECKS PASSED (N/N)` to stdout
