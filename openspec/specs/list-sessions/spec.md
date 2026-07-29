## ADDED Requirements

### Requirement: List active sessions
The `isolagent list` subcommand SHALL query libvirt for all domains (any state) whose names start with `isolagent-` and display them in a formatted table.

#### Scenario: Active sessions found
- **WHEN** the user runs `isolagent list` and isolagent domains exist
- **THEN** a table is printed with columns: Domain, Profile, Guest IP, State

#### Scenario: No active sessions
- **WHEN** the user runs `isolagent list` and no isolagent domains exist
- **THEN** the message "No active sessions" is printed

#### Scenario: libvirt not reachable
- **WHEN** the user runs `isolagent list` and libvirtd is not reachable
- **THEN** an error is printed to stderr and the process exits with code 1

### Requirement: Profile name extracted from domain XML metadata
The list command SHALL extract the profile name from the domain XML's `<isolagent:profile>` element (namespace `http://isolagent.local/`). If the element is missing or parsing fails, the profile column SHALL be empty.

#### Scenario: Profile metadata present
- **WHEN** a domain's XML contains `<isolagent:profile>example</isolagent:profile>`
- **THEN** the Profile column shows `example`

#### Scenario: Profile metadata missing
- **WHEN** a domain's XML does not contain the isolagent namespace metadata
- **THEN** the Profile column is empty

### Requirement: Guest IP discovered via DHCP lease
The list command SHALL discover the guest IP via `domain.interfaceAddresses` using the DHCP lease source. It SHALL use the first non-loopback IPv4 address found. If no address is available, the Guest IP column SHALL show `pending`.

#### Scenario: Guest IP available
- **WHEN** a domain has a DHCP lease with a non-loopback IPv4 address
- **THEN** the Guest IP column shows that address

#### Scenario: Guest IP not yet assigned
- **WHEN** a domain has no DHCP lease or the query fails
- **THEN** the Guest IP column shows `pending`

### Requirement: Domain state mapped to human-readable name
The list command SHALL map numeric libvirt domain states to human-readable names (nostate, running, blocked, paused, shutdown, shutoff, crashed, suspended). Unknown state numbers SHALL display as `unknown(<number>)`.

#### Scenario: Running domain
- **WHEN** a domain's state number is 1
- **THEN** the State column shows `running`

#### Scenario: Unknown state
- **WHEN** a domain's state number is not in the known set
- **THEN** the State column shows `unknown(<number>)`
