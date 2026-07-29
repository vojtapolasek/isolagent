### Requirement: Test profile exists as a real on-disk profile
A test profile SHALL exist at `profiles/test/profile.yaml` as a complete, schema-valid profile with placeholder paths for host-dependent fields.

#### Scenario: Profile is schema-valid on its own
- **WHEN** the test profile is loaded from `profiles/test/profile.yaml`
- **THEN** it passes JSON Schema validation
- **AND** path fields contain placeholder values (e.g., `/must-be-overridden`)

#### Scenario: Profile uses Fedora OS role
- **WHEN** the test profile is loaded
- **THEN** `image.os` is `fedora`, and the base image URL is resolved from the fedora role's `vars/main.yaml`

### Requirement: Test profile includes guest files
The test profile SHALL include a `profiles/test/guest-files/root/.test-marker` file with content `isolagent-test-ok`. The `root/` prefix mirrors the guest filesystem — the file is deployed to `/root/.test-marker` on the guest.

#### Scenario: Guest file is present
- **WHEN** the test profile directory is examined
- **THEN** `profiles/test/guest-files/root/.test-marker` exists with content `isolagent-test-ok`

### Requirement: Test profile defines test environment variables
The test profile SHALL define `agent.env` with at least two variables: `SANDBOX_TEST_VAR=expected-value` and `SANDBOX_TEST_EMPTY=""`.

#### Scenario: Env vars are defined in profile
- **WHEN** the test profile is loaded
- **THEN** `agent.env.SANDBOX_TEST_VAR` equals `expected-value`
- **AND** `agent.env.SANDBOX_TEST_EMPTY` equals `""`

### Requirement: Agent test script validates sandbox from inside the VM
The agent script SHALL verify sandbox capabilities from inside the VM and write structured JSON results to `/tmp/test-results.json`.

#### Scenario: Script checks environment variables
- **WHEN** the agent script runs inside the VM
- **THEN** it verifies `SANDBOX_TEST_VAR` equals `expected-value`
- **AND** it verifies `SANDBOX_TEST_EMPTY` is set and equals empty string

#### Scenario: Script checks project sync
- **WHEN** the agent script runs inside the VM
- **THEN** it verifies the workdir contents arrived at the expected mount point under `/isolagent/`

#### Scenario: Script checks extra syncs
- **WHEN** the agent script runs inside the VM with extra_syncs configured
- **THEN** it verifies each extra sync directory arrived at `/isolagent/<basename>`

#### Scenario: Script checks guest files
- **WHEN** the agent script runs inside the VM
- **THEN** it verifies `~/.test-marker` exists with content `isolagent-test-ok`

#### Scenario: Script produces file changes for output extraction
- **WHEN** the agent script runs inside the VM
- **THEN** it modifies a file in the synced workdir so output modes have a diff to extract

#### Scenario: Script exits non-zero on failure
- **WHEN** any verification check fails
- **THEN** the script exits with a non-zero exit code
- **AND** `/tmp/test-results.json` contains details of which checks failed
