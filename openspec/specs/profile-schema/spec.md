## Requirements

### Requirement: Profile is a YAML file with name, image, agent, project, and optional runtime sections
A profile SHALL be a YAML file containing top-level keys: `name`, `image`, `agent`, and `project`. The `runtime` section is optional and defaults to an empty object.

#### Scenario: Complete profile
- **WHEN** a YAML file contains all required sections (`name`, `image`, `agent`, `project`) and optionally `runtime`
- **THEN** it is a valid profile

#### Scenario: Missing required section
- **WHEN** a YAML file is missing the `agent` section
- **THEN** validation fails with an error identifying the missing section

### Requirement: Image section defines OS and roles
The `image` section SHALL contain `os` (string, required, validated at build time against available OS role directories) and `roles` (array of strings, optional, defaults to empty list).

#### Scenario: Valid image section
- **WHEN** the image section contains `os: "fedora"` and `roles: ["agent-claude", "my-custom-role"]`
- **THEN** validation passes for the image section

#### Scenario: Minimal image section
- **WHEN** the image section contains only `os: "fedora"`
- **THEN** validation passes with `roles` defaulted to empty list

#### Scenario: Missing os field
- **WHEN** the image section is missing `os`
- **THEN** validation fails with an error identifying the missing field

#### Scenario: Unknown os value
- **WHEN** the image section contains `os: "windows"` and the builder attempts to load OS role vars
- **THEN** the builder fails with an error indicating the OS role was not found

### Requirement: Agent section defines launch only
The `agent` section SHALL contain `command` (string, required) and `env` (map of string to string, optional, defaults to empty).

#### Scenario: Minimal agent section
- **WHEN** the agent section contains only `command: "claude --dangerously-skip-permissions"`
- **THEN** validation passes with `env` defaulted to empty

#### Scenario: Full agent section
- **WHEN** the agent section contains `command` and `env`
- **THEN** validation passes with all values populated

### Requirement: Runtime section defines session parameters
The `runtime` section SHALL contain: `access_host_libvirt` (boolean, default false), `libvirt_uri` (string, optional), `memory` (string, default "4G"), `cpus` (integer, default 4), `disk` (string, default "20G"). Output mode and output directory are CLI-only arguments on `isolagent run`, not part of the profile.

The `access_host_libvirt` field replaces the former `libvirt` field. When true, the session starts a host-side socat relay so the guest can reach the host's libvirtd via VSOCK.

The `libvirt_uri` field specifies which libvirt connection URI to use for VM management (e.g., `qemu:///session`). If omitted, defaults to `qemu:///system`. The `ISOLAGENT_LIBVIRT_URI` environment variable takes precedence over this field.

The `disk` field specifies the usable disk size for the session VM (overlay disk virtual size and grown root filesystem). It SHALL be a positive integer followed by the unit suffix `M`, `G`, or `T` (e.g., `"20G"`, `"512M"`, `"1T"`).

#### Scenario: Minimal runtime section
- **WHEN** the runtime section is empty or omitted
- **THEN** validation passes with `access_host_libvirt` defaulted to false, `libvirt_uri` unset, `memory` to "4G", `cpus` to 4, and `disk` to "20G"

#### Scenario: Valid disk value
- **WHEN** the runtime section contains `disk: "40G"`
- **THEN** validation passes with `disk` set to "40G"

#### Scenario: Invalid disk value
- **WHEN** the runtime section contains `disk: "big"` or `disk: "40"` (no unit suffix)
- **THEN** profile validation fails with an error identifying the invalid disk size format

#### Scenario: Host libvirt access enabled
- **WHEN** the runtime section contains `access_host_libvirt: true`
- **THEN** the session enables the VSOCK socat relay for host libvirtd access

#### Scenario: Custom libvirt URI
- **WHEN** the runtime section contains `libvirt_uri: "qemu:///session"`
- **THEN** the session connects to `qemu:///session` instead of `qemu:///system`

#### Scenario: Environment variable overrides profile URI
- **WHEN** the profile sets `libvirt_uri: "qemu:///session"` and `ISOLAGENT_LIBVIRT_URI=qemu+ssh://remote/system` is set
- **THEN** the session connects to `qemu+ssh://remote/system`

### Requirement: Project section defines workdir and extra syncs
The `project` section SHALL contain `workdir` (string path, required) and `extra_syncs` (list of string paths, optional, defaults to empty).

#### Scenario: Workdir only
- **WHEN** the project section contains only `workdir: "~/repos/content"`
- **THEN** validation passes with `extra_syncs` defaulted to empty list

#### Scenario: Workdir with extra syncs
- **WHEN** the project section contains `workdir` and `extra_syncs: ["/path/a", "/path/b"]`
- **THEN** validation passes with both values populated

### Requirement: Example profile validates against schema
The project SHALL maintain a profile at `profiles/example/` whose `profile.yaml` validates against `profile_schema.json`. Any change to the schema MUST be accompanied by a corresponding update to the example profile.

#### Scenario: Schema field added
- **WHEN** a new field is added to `profile_schema.json`
- **THEN** `profiles/example/profile.yaml` is updated to include the new field

#### Scenario: CI-equivalent validation
- **WHEN** `profiles/example/profile.yaml` is validated against `profile_schema.json`
- **THEN** validation passes with no errors

### Requirement: Profile supports tilde and variable expansion
All path fields in the profile SHALL expand `~` and environment variables (`$VAR`, `${VAR}`) at load time.

#### Scenario: Tilde expansion
- **WHEN** a profile contains `workdir: "~/repos/content"`
- **THEN** the loaded profile expands it to the user's home directory (e.g. `/home/user/repos/content`)

#### Scenario: Environment variable expansion
- **WHEN** a profile contains `workdir: "$HOME/repos/content"`
- **THEN** the loaded profile expands `$HOME` to its value
