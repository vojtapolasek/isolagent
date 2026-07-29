## ADDED Requirements

### Requirement: Content sync into guest
The session module SHALL rsync `project.workdir` from the host to `/isolagent/project/` on the guest. Additionally, each entry in `project.extra_syncs` SHALL be rsynced to `/isolagent/<basename>/`.

#### Scenario: Primary project sync
- **WHEN** the session setup phase runs
- **THEN** `project.workdir` is rsynced to `/isolagent/project/` with `--delete --chown=root:root`

#### Scenario: Extra syncs
- **WHEN** `project.extra_syncs` contains `["/home/user/data", "/home/user/tools"]`
- **THEN** `/home/user/data` is rsynced to `/isolagent/data/` and `/home/user/tools` to `/isolagent/tools/`

#### Scenario: No extra syncs
- **WHEN** `project.extra_syncs` is empty
- **THEN** only `project.workdir` is synced

#### Scenario: Basename collision between extra_syncs
- **WHEN** `project.extra_syncs` contains `["/home/user/project-a/data", "/home/user/project-b/data"]`
- **THEN** the session errors before syncing: both map to `/isolagent/data/`

#### Scenario: Extra sync collides with primary project
- **WHEN** `project.extra_syncs` contains an entry with basename `project`
- **THEN** the session errors before syncing: conflicts with `/isolagent/project/`

