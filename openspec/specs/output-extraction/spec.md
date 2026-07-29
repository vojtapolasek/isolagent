## ADDED Requirements

### Requirement: Output mode is mandatory for agent sessions
The `isolagent run` CLI SHALL require `--output-mode` as a mandatory argument when running an agent session. It is not part of the profile — it is a per-session decision. Valid values are `patch`, `sync`, and `none`. When `--shell` is used, `--output-mode` is not required and output extraction is skipped entirely.

#### Scenario: Missing output_mode (agent session)
- **WHEN** the user runs `isolagent run myprofile` without `--output-mode` and without `--shell`
- **THEN** the CLI rejects the command with an error about the missing required argument

#### Scenario: Shell mode ignores output
- **WHEN** the user runs `isolagent run myprofile --shell`
- **THEN** output extraction is skipped entirely regardless of whether `--output-mode` is passed

### Requirement: Patch output mode
When output mode is `patch`, the session SHALL extract agent commits as a git format-patch file saved to `--output-dir` (defaults to `project.workdir`). Preflight SHALL validate that the project is a git repository with at least one commit before booting the VM. During setup, the session SHALL disable git hooks in the guest via `git config core.hooksPath /dev/null` to prevent hooks from interfering with agent commits or `git format-patch`.

#### Scenario: Agent made commits (default output dir)
- **WHEN** the agent created commits during the session, output mode is `patch`, and no `--output-dir` is specified
- **THEN** the session runs `git format-patch <initial_head> --stdout` in the guest and saves the result to `<workdir>/isolagent-<timestamp>.patch`
- **THEN** the session prints apply instructions: `cd <workdir> && git am <patchfile>`

#### Scenario: Agent made commits (custom output dir)
- **WHEN** the agent created commits during the session, output mode is `patch`, and `--output-dir` is `/home/user/patches`
- **THEN** the session saves the patch file to `/home/user/patches/isolagent-<timestamp>.patch`

#### Scenario: No commits made
- **WHEN** the agent made no commits and output mode is `patch`
- **THEN** the session prints "No commits made by agent" and does not create a patch file

#### Scenario: Uncommitted changes present
- **WHEN** the agent left uncommitted changes in the guest working tree
- **THEN** the session warns about uncommitted changes not included in the patch

#### Scenario: Project is not a git repo
- **WHEN** `--output-mode patch` is used and the project directory is not a git repository
- **THEN** the session fails during preflight with a clear error before booting the VM

#### Scenario: Project has no commits
- **WHEN** `--output-mode patch` is used and the project directory is a git repo with no commits
- **THEN** the session fails during preflight with a clear error before booting the VM

### Requirement: Sync output mode
When output mode is `sync`, the session SHALL rsync the guest project directory back to `--output-dir` on the host. The `--output-dir` argument is required for sync mode. Rsync SHALL always use `--delete` to produce an exact mirror of the guest state, regardless of whether the output directory matches the workdir.

#### Scenario: Sync to custom directory
- **WHEN** output mode is `sync` and `--output-dir` is `/home/user/output`
- **THEN** the session rsync's `/isolagent/project/` to `/home/user/output/` with `--delete`

#### Scenario: Sync to workdir explicitly
- **WHEN** output mode is `sync` and `--output-dir` is set to the same path as `project.workdir`
- **THEN** the session rsync's `/isolagent/project/` to `project.workdir` with `--delete`
- **AND** `--overwrite` is required because the directory is non-empty

#### Scenario: Sync without output-dir
- **WHEN** output mode is `sync` and `--output-dir` is not specified
- **THEN** the CLI rejects the command with an error: "--output-dir is required when using --output-mode sync"

#### Scenario: Agent deletions are mirrored
- **WHEN** the agent deletes a file during the session and output mode is `sync`
- **THEN** the deleted file is also removed from the output directory by rsync `--delete`

### Requirement: None output mode
When output mode is `none`, the session SHALL skip output extraction entirely.

#### Scenario: Output discarded
- **WHEN** output mode is `none`
- **THEN** the session prints "Output mode is 'none' — changes discarded" and performs no extraction

### Requirement: Output extraction is resilient
Output extraction SHALL handle the case where the VM is unreachable (crashed, shutdown) by warning and continuing teardown. Other extraction errors (disk full, permission changes) SHALL be printed as warnings but SHALL NOT prevent VM cleanup from proceeding.

#### Scenario: VM unreachable during extraction
- **WHEN** the VM has crashed and SSH is not available during teardown
- **THEN** the session warns "VM unreachable, skipping output extraction" and continues with cleanup

#### Scenario: Extraction error during teardown
- **WHEN** output extraction fails for a reason other than VM unreachability (e.g., disk full)
- **THEN** the session prints the error as a warning and continues with VM cleanup

### Requirement: Overwrite flag for sync mode
The CLI SHALL accept an `--overwrite` flag. When `--output-mode sync` targets a non-empty directory, `--overwrite` is required. The flag is silently ignored for other output modes.

#### Scenario: Overwrite flag with patch mode
- **WHEN** the user passes `--overwrite` with `--output-mode patch`
- **THEN** the flag is silently ignored

#### Scenario: Overwrite flag with none mode
- **WHEN** the user passes `--overwrite` with `--output-mode none`
- **THEN** the flag is silently ignored
