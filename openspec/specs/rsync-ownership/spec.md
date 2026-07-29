### Requirement: Sync-in sets root ownership
The sync-in rsync command SHALL set file ownership to `root:root` on all transferred files inside the guest VM.

#### Scenario: Content synced into guest is owned by root
- **WHEN** `SessionRunner` syncs content from the host into the guest via rsync
- **THEN** all files under `/isolagent/project/` are owned by `root:root`

#### Scenario: Git operates without safe.directory error
- **WHEN** a git command (e.g., `git log`, `git shortlog -se`, `git diff`) is run as root inside the guest on `/isolagent/project/`
- **THEN** the command executes successfully without a "dubious ownership" error

