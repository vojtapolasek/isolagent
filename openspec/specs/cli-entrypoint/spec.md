## ADDED Requirements

### Requirement: CLI provides subcommand dispatch
The `isolagent` CLI SHALL accept the subcommands `build`, `run`, and `list`. Each subcommand SHALL be a distinct entry point. The `setup-host` and `teardown-host` subcommands are removed.

#### Scenario: Valid subcommand
- **WHEN** the user runs `isolagent run example`
- **THEN** the CLI dispatches to the `run` handler with `example` as the profile name

#### Scenario: No subcommand
- **WHEN** the user runs `isolagent` with no subcommand
- **THEN** the CLI prints usage help listing all available subcommands and exits with code 0

#### Scenario: Unknown subcommand
- **WHEN** the user runs `isolagent foo`
- **THEN** the CLI prints an error message indicating `foo` is not a valid subcommand and exits with a non-zero code

#### Scenario: Removed subcommand
- **WHEN** the user runs `isolagent setup-host`
- **THEN** the CLI prints an error message indicating `setup-host` is not a valid subcommand

### Requirement: Run subcommand accepts profile and runtime overrides
The `run` subcommand SHALL require a profile name as a positional argument. It SHALL accept optional flags: `--memory`, `--cpus`, `--output-mode`, `--output-dir`, `--overwrite`, `--shell`, and `--profiles-dir`. The `--slot` argument SHALL NOT exist — slot allocation is automatic. `--output-mode` is required unless `--shell` is used.

#### Scenario: Run with profile and output mode
- **WHEN** the user runs `isolagent run myprofile --output-mode patch`
- **THEN** the CLI loads the profile `myprofile` and uses its runtime defaults

#### Scenario: Run with overrides
- **WHEN** the user runs `isolagent run myprofile --output-mode patch --memory 8G --cpus 8`
- **THEN** the CLI loads the profile `myprofile` and overrides memory to `8G` and cpus to `8`, keeping all other values from the profile

#### Scenario: Unknown flag --prompt
- **WHEN** the user runs `isolagent run myprofile --prompt "hello"`
- **THEN** the CLI prints an error indicating `--prompt` is not a recognized argument and exits with a non-zero code

### Requirement: Build subcommand accepts profile name
The `build` subcommand SHALL require a profile name as a positional argument. It SHALL accept `--profiles-dir` to override the default profiles directory and `--force` to skip the rebuild confirmation prompt.

#### Scenario: Build with profile
- **WHEN** the user runs `isolagent build myprofile`
- **THEN** the CLI loads the profile `myprofile` and dispatches to the build handler

#### Scenario: Force rebuild
- **WHEN** the user runs `isolagent build myprofile --force` and the image already exists
- **THEN** the existing image is replaced without prompting for confirmation

### Requirement: List subcommand takes no arguments
The `list` subcommand SHALL take no required arguments and SHALL display information about active sandbox sessions.

#### Scenario: List sessions
- **WHEN** the user runs `isolagent list`
- **THEN** the CLI dispatches to the list handler

### Requirement: Subcommands are fully implemented
The `run` subcommand SHALL call the session module to execute a full VM session. The `list` subcommand SHALL query libvirt and display active sessions.

#### Scenario: Run executes a session
- **WHEN** the user runs `isolagent run myprofile --output-mode patch`
- **THEN** the CLI loads the profile, creates a SessionRunner, and executes the full lifecycle (preflight → init → setup → run → teardown)

#### Scenario: List shows active sessions
- **WHEN** the user runs `isolagent list`
- **THEN** the CLI queries libvirt for running `isolagent-*` domains and displays them with domain name, profile, guest IP, and state

#### Scenario: List with no sessions
- **WHEN** the user runs `isolagent list` and no sessions are active
- **THEN** the CLI prints "No active sessions"

### Requirement: Run subcommand accepts shell mode flag
The `run` subcommand SHALL accept `--shell` to drop into an interactive SSH shell instead of running the agent.

#### Scenario: Shell mode
- **WHEN** the user runs `isolagent run myprofile --shell`
- **THEN** the session starts in shell mode (interactive bash at `/isolagent/project/`)
