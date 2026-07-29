## ADDED Requirements

### Requirement: Output directory must exist
When `--output-dir` is specified, preflight SHALL verify that the directory exists. If it does not exist, preflight SHALL raise a `SessionError` with a message suggesting `mkdir` to create it. The directory SHALL NOT be created automatically.

#### Scenario: Output directory does not exist
- **WHEN** the user runs `isolagent run myprofile --output-mode patch --output-dir /tmp/nonexistent`
- **THEN** preflight fails with an error: "/tmp/nonexistent does not exist — create it with: mkdir -p /tmp/nonexistent"

#### Scenario: Output directory exists
- **WHEN** the user runs `isolagent run myprofile --output-mode patch --output-dir /tmp/patches` and `/tmp/patches` exists
- **THEN** preflight passes the existence check

### Requirement: Output directory must be writable
When `--output-dir` is specified, preflight SHALL verify that the directory is writable using `os.access(path, os.W_OK)`. If it is not writable, preflight SHALL raise a `SessionError`.

#### Scenario: Output directory is not writable
- **WHEN** the user runs `isolagent run myprofile --output-mode sync --output-dir /readonly-dir --overwrite` and the directory is not writable
- **THEN** preflight fails with an error indicating the directory is not writable

#### Scenario: Output directory is writable
- **WHEN** the user runs `isolagent run myprofile --output-mode patch --output-dir /tmp/patches` and the directory is writable
- **THEN** preflight passes the writability check

### Requirement: Sync mode requires empty directory unless overwrite
When `--output-mode sync` is used and `--output-dir` is specified, preflight SHALL verify that the directory is empty unless `--overwrite` is passed. If the directory is non-empty and `--overwrite` is not set, preflight SHALL raise a `SessionError`.

#### Scenario: Sync to non-empty directory without overwrite
- **WHEN** the user runs `isolagent run myprofile --output-mode sync --output-dir /tmp/output` and `/tmp/output` contains files
- **THEN** preflight fails with an error indicating the directory is not empty and suggesting `--overwrite`

#### Scenario: Sync to non-empty directory with overwrite
- **WHEN** the user runs `isolagent run myprofile --output-mode sync --output-dir /tmp/output --overwrite` and `/tmp/output` contains files
- **THEN** preflight passes the emptiness check

#### Scenario: Sync to empty directory without overwrite
- **WHEN** the user runs `isolagent run myprofile --output-mode sync --output-dir /tmp/output` and `/tmp/output` is empty
- **THEN** preflight passes the emptiness check

#### Scenario: Patch mode ignores emptiness
- **WHEN** the user runs `isolagent run myprofile --output-mode patch --output-dir /tmp/patches` and `/tmp/patches` contains files
- **THEN** preflight does not check emptiness — patch mode writes a single timestamped file

### Requirement: No lazy directory creation in patch extraction
Patch extraction SHALL NOT create the output directory lazily with `mkdir(parents=True)`. The preflight check guarantees the directory exists before the VM boots.

#### Scenario: Patch extraction uses existing directory
- **WHEN** patch extraction runs after a successful preflight
- **THEN** the patch file is written directly to the output directory without attempting to create it
