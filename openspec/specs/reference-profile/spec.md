## ADDED Requirements

### Requirement: Reference profile demonstrates all schema options
The project SHALL include a profile at `profiles/reference/` that contains a `profile.yaml` exercising every field defined in `profile_schema.json`. The profile MUST validate against the JSON schema. It does not need to be functionally bootable.

#### Scenario: Reference profile validates against schema
- **WHEN** the reference profile's `profile.yaml` is validated against `profile_schema.json`
- **THEN** validation passes with no errors

#### Scenario: Reference profile shows all optional fields
- **WHEN** a user reads `profiles/reference/profile.yaml`
- **THEN** every field from the schema is present, including optional fields with their defaults shown explicitly

### Requirement: Reference profile includes full directory structure
The reference profile SHALL include a custom role directory (`roles/my-custom-role/tasks/main.yaml`) and a guest-files directory demonstrating the complete profile layout.

#### Scenario: User sees custom role example
- **WHEN** a user reads `profiles/reference/roles/my-custom-role/tasks/main.yaml`
- **THEN** they find example Ansible tasks showing package installation and file creation

#### Scenario: User sees guest-files example
- **WHEN** a user reads the reference profile's `guest-files/` directory
- **THEN** they find sample files demonstrating how to provide configuration to the agent

### Requirement: Schema changes must update the reference profile
When the profile schema (`profile_schema.json`) changes, the reference profile MUST be updated to reflect the new schema. This rule SHALL be documented in the project's CLAUDE.md.

#### Scenario: New field added to schema
- **WHEN** a developer adds a new field to `profile_schema.json`
- **THEN** the CLAUDE.md convention reminds them to add the field to `profiles/reference/profile.yaml`

#### Scenario: Field removed from schema
- **WHEN** a developer removes a field from `profile_schema.json`
- **THEN** the CLAUDE.md convention reminds them to remove the field from `profiles/reference/profile.yaml`
