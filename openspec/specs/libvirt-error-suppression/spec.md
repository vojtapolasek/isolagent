### Requirement: Suppress libvirt C-level stderr output
The CLI MUST register a no-op libvirt error handler before any libvirt API calls to prevent the C library's default error handler from writing to stderr.

#### Scenario: Normal build invocation
- **WHEN** the user runs `isolagent build <profile>` and no stale build VM exists
- **THEN** no libvirt error messages SHALL appear on stderr

#### Scenario: Normal run invocation
- **WHEN** the user runs `isolagent run --output-mode none <profile>`
- **THEN** no libvirt error messages SHALL appear on stderr

#### Scenario: Python exceptions still raised
- **WHEN** a libvirt API call fails (e.g., domain not found, volume not found)
- **THEN** the Python `libvirtError` exception MUST still be raised with the full error message
- **AND** all existing `try/except libvirtError` handling MUST continue to work unchanged
