### Requirement: Preflight validates workdir exists for patch mode
When `--output-mode patch` is requested, `preflight()` SHALL first verify that `project.workdir` exists as a directory. If the directory does not exist, preflight SHALL raise a `SessionError`.

#### Scenario: Workdir does not exist
- **WHEN** `--output-mode patch` is used and `project.workdir` does not exist
- **THEN** preflight raises `SessionError` with a message stating the path does not exist

### Requirement: Preflight validates git work tree for patch mode
When `--output-mode patch` is requested, `preflight()` SHALL verify that `project.workdir` is inside a git work tree by running `git rev-parse --is-inside-work-tree` on the host. If the check fails, preflight SHALL raise a `SessionError` before any VM resources are allocated.

#### Scenario: Project is a git repo
- **WHEN** `--output-mode patch` is used and `project.workdir` is inside a git work tree
- **THEN** preflight passes this check and continues

#### Scenario: Project is not a git repo
- **WHEN** `--output-mode patch` is used and `project.workdir` is not inside a git work tree
- **THEN** preflight raises `SessionError` with a message stating the path is not a git repository and that `--output-mode patch` requires one

#### Scenario: Non-patch output modes skip the check
- **WHEN** `--output-mode sync` or `--output-mode none` is used
- **THEN** preflight does not run the git work tree check

### Requirement: Preflight validates git HEAD exists for patch mode
When `--output-mode patch` is requested and the project is a git work tree, `preflight()` SHALL verify that at least one commit exists by running `git rev-parse HEAD` on the host. If the check fails, preflight SHALL raise a `SessionError`.

#### Scenario: Project has commits
- **WHEN** `--output-mode patch` is used and `project.workdir` has at least one commit
- **THEN** preflight passes this check and continues

#### Scenario: Project is an empty git repo with no commits
- **WHEN** `--output-mode patch` is used and `project.workdir` is a git repo with no commits
- **THEN** preflight raises `SessionError` with a message stating the project has no commits and advising to make an initial commit before using patch mode
