## MODIFIED Requirements

### Requirement: Content available before agent starts
The VM launch process SHALL rsync the content project into the guest before the agent launches, so that the agent has access to the files from the start.

#### Scenario: Fresh VM launch
- **WHEN** `isolagent run` launches a VM and SSH becomes available
- **THEN** the project content SHALL be present at `/isolagent/project` before the agent starts

### Requirement: Agent starts in the content directory
In unattended mode, the agent command SHALL be launched with its working directory set to `/isolagent/project`. In interactive mode, the SSH shell SHALL start in `/isolagent/project`.

#### Scenario: Unattended mode working directory
- **WHEN** `isolagent run` starts the agent via SSH
- **THEN** the agent's working directory SHALL be `/isolagent/project`

#### Scenario: Interactive mode working directory
- **WHEN** the user runs `isolagent run --shell`
- **THEN** the shell's working directory SHALL be `/isolagent/project`

### Requirement: Agent-specific trust configured via profile
Profiles that run agents requiring project trust (e.g., Claude Code) SHOULD include the appropriate trust configuration as a guest file so the agent recognizes `/isolagent/project` as trusted without prompting. This is a profile-level responsibility delivered via `guest-files/`, not baked into the base image.

#### Scenario: No trust prompt on connect
- **WHEN** the agent starts in `/isolagent/project` and the profile provides the appropriate trust configuration
- **THEN** the agent SHALL NOT prompt for project trust approval

## MODIFIED Requirements

### Requirement: Directory exists before upload
The prebaked base image SHALL include an empty `/isolagent/project` directory, ready for rsync to populate.

#### Scenario: Directory exists in image
- **WHEN** the VM boots from the prebaked image
- **THEN** `/isolagent/project` exists as an empty directory
