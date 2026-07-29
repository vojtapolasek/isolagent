## ADDED Requirements

### Requirement: Profile guest file directory
A profile directory MAY contain a `guest-files/` subdirectory. When present, its internal structure SHALL mirror the absolute paths where files are placed inside the guest VM.

#### Scenario: File at mirrored path
- **WHEN** a profile has `guest-files/root/.claude.json`
- **THEN** it is uploaded to `/root/.claude.json` inside the guest at session time

#### Scenario: Nested path
- **WHEN** a profile has `guest-files/isolagent/project/CLAUDE.md`
- **THEN** it is uploaded to `/isolagent/project/CLAUDE.md` inside the guest

#### Scenario: No guest-files directory
- **WHEN** a profile directory does not contain a `guest-files/` subdirectory
- **THEN** no guest files are deployed and no error is raised

### Requirement: Guest files deployed at session time via SCP
The session runner SHALL walk the profile's `guest-files/` tree and SCP each file to the guest after SSH is available.

#### Scenario: All files deployed
- **WHEN** a profile has three files under `guest-files/`
- **THEN** all three are SCP'd to the guest at their mirrored paths before the agent starts

#### Scenario: Directories created on guest
- **WHEN** a guest file's destination directory does not exist on the guest
- **THEN** the session runner SHALL create the directory before uploading the file

#### Scenario: SCP failure
- **WHEN** SCP fails for a guest file
- **THEN** the session raises a `SessionError` identifying the file and the error

### Requirement: Guest files not baked into image at build time
The image build pipeline SHALL NOT deploy profile guest files into the image. Guest files are a session-time concern only.

#### Scenario: Build without guest files
- **WHEN** `isolagent build <profile>` runs
- **THEN** no files from the profile's `guest-files/` directory are included in the built image
