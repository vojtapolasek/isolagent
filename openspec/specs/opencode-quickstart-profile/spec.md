## Purpose

Define the opencode quickstart profile -- a minimal, bootable sandbox profile that uses the opencode agent with no external dependencies like litellm.

## Requirements

### Requirement: Quickstart profile exists with minimal configuration
The project SHALL include a profile at `profiles/opencode-quickstart/` containing a `profile.yaml` that provides a working, bootable sandbox using opencode. The profile SHALL use the `agent-opencode` role, launch opencode with `--auto` flag, and require no environment variables.

#### Scenario: Profile validates against schema
- **WHEN** the quickstart profile's `profile.yaml` is validated against `profile_schema.json`
- **THEN** validation passes with no errors

#### Scenario: Profile uses opencode agent role
- **WHEN** a user reads the quickstart profile's `image.roles`
- **THEN** the list contains `agent-opencode` and no other roles

#### Scenario: Agent command enables autonomous operation
- **WHEN** a user reads the quickstart profile's `agent.command`
- **THEN** the value is `opencode --auto`

#### Scenario: No environment variables required
- **WHEN** a user reads the quickstart profile's `agent.env`
- **THEN** the field is either absent or an empty object

#### Scenario: Default runtime resources
- **WHEN** a user reads the quickstart profile's `runtime` section
- **THEN** no runtime fields are specified (schema defaults apply: 4G memory, 4 CPUs, no libvirt access)

#### Scenario: No guest-files directory
- **WHEN** a user inspects the `profiles/opencode-quickstart/` directory
- **THEN** there is no `guest-files/` subdirectory

### Requirement: Quickstart profile uses placeholder workdir
The quickstart profile SHALL set `project.workdir` to `~/my-project` as a placeholder. Documentation SHALL note that this is the one field users must change before running.

#### Scenario: Workdir is a placeholder
- **WHEN** a user reads the quickstart profile's `project.workdir`
- **THEN** the value is `~/my-project`
