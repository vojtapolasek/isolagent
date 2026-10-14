# Spec Delta

## MODIFIED Requirements

### Requirement: Run subcommand accepts profile and runtime overrides
The `run` subcommand SHALL require a profile name as a positional argument. It SHALL accept optional flags: `--memory`, `--cpus`, `--disk`, `--output-mode`, `--output-dir`, `--overwrite`, `--shell`, and `--profiles-dir`. The `--slot` argument SHALL NOT exist — slot allocation is automatic. `--output-mode` is required unless `--shell` is used.

#### Scenario: Run with profile and output mode
- **WHEN** the user runs `isolagent run myprofile --output-mode patch`
- **THEN** the CLI loads the profile `myprofile` and uses its runtime defaults

#### Scenario: Run with overrides
- **WHEN** the user runs `isolagent run myprofile --output-mode patch --memory 8G --cpus 8`
- **THEN** the CLI loads the profile `myprofile` and overrides memory to `8G` and cpus to `8`, keeping all other values from the profile

#### Scenario: Run with disk override
- **WHEN** the user runs `isolagent run myprofile --output-mode patch --disk 40G`
- **THEN** the CLI loads the profile `myprofile` and overrides `runtime.disk` to `40G`, keeping all other values from the profile

#### Scenario: Unknown flag --prompt
- **WHEN** the user runs `isolagent run myprofile --prompt "hello"`
- **THEN** the CLI prints an error indicating `--prompt` is not a recognized argument and exits with a non-zero code
