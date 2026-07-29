## ADDED Requirements

### Requirement: Profiles are discovered from a profiles directory
The system SHALL look for profile directories in a `profiles/` directory relative to the project root. Each subdirectory containing a `profile.yaml` file is a profile. The profile name is the subdirectory name.

#### Scenario: Profile found by name
- **WHEN** the user specifies profile name `example`
- **THEN** the system loads `profiles/example/profile.yaml`

#### Scenario: Profile not found
- **WHEN** the user specifies profile name `nonexistent`
- **THEN** the system prints an error listing available profiles and exits with a non-zero code

#### Scenario: No profiles directory
- **WHEN** the `profiles/` directory does not exist
- **THEN** the system prints an error indicating no profiles directory was found

#### Scenario: Subdirectory without profile.yaml
- **WHEN** a subdirectory exists in `profiles/` but does not contain `profile.yaml`
- **THEN** that subdirectory is not listed as an available profile

### Requirement: Profile loading returns profile directory
After loading and validation, the system SHALL inject the profile directory path as `_profile_dir` into the profile object so that session code can locate the `guest-files/` subdirectory. Because `_profile_dir` is not part of the profile schema (`additionalProperties: false`), it is added after `validate_profile()` returns. Callers SHOULD NOT re-validate the profile object after loading.

#### Scenario: Profile directory available
- **WHEN** a profile is loaded from `profiles/example/profile.yaml`
- **THEN** the profile object has `_profile_dir` set to the absolute path of `profiles/example/`

### Requirement: Profile loading validates against schema
After parsing the YAML, the system SHALL validate the profile against the jsonschema. Validation errors SHALL be reported with the specific field path and constraint that failed.

#### Scenario: Valid profile loads successfully
- **WHEN** a profile YAML passes schema validation
- **THEN** the system returns a validated profile object with all defaults applied

#### Scenario: Invalid profile reports clear errors
- **WHEN** a profile YAML has `runtime.cpus: "not-a-number"`
- **THEN** the system reports a validation error identifying `runtime.cpus` and the type constraint

### Requirement: Profile loading applies defaults before validation
The system SHALL apply default values for optional fields before performing validation. This ensures that validation operates on fully populated data.

#### Scenario: Defaults applied
- **WHEN** a profile omits the entire `runtime` section
- **THEN** the loaded profile has `runtime.access_host_libvirt` set to `false`, `runtime.memory` set to `"4G"`, `runtime.cpus` set to `4`, `runtime.libvirt_uri` unset, and all other runtime fields set to their defaults

### Requirement: CLI overrides merge on top of profile values
When the CLI provides runtime override flags, those values SHALL replace the corresponding profile values after loading and validation.

#### Scenario: CLI override replaces profile value
- **WHEN** a profile has `runtime.memory: "4G"` and the CLI passes `--memory 8G`
- **THEN** the effective configuration has memory set to `"8G"`

#### Scenario: CLI override does not affect other fields
- **WHEN** the CLI passes only `--memory 8G`
- **THEN** all other profile values remain unchanged

### Requirement: Environment variables injected inline with agent command
The session runner SHALL prepend `agent.env` key-value pairs to the `agent.command` invocation using `env KEY=VALUE` syntax.

#### Scenario: Env vars passed to agent
- **WHEN** `agent.env` contains `{"ANTHROPIC_API_KEY": "unused", "IS_SANDBOX": "1"}`
- **THEN** the agent is started with `env ANTHROPIC_API_KEY=unused IS_SANDBOX=1 <agent.command>`

#### Scenario: No env vars
- **WHEN** `agent.env` is empty
- **THEN** the agent command is executed without an `env` prefix

#### Scenario: Env vars with special characters
- **WHEN** an env var value contains spaces or shell-special characters
- **THEN** the value SHALL be properly shell-quoted in the command
