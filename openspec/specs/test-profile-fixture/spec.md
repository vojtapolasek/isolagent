### Requirement: Integration test fixtures use directory-based profile layout
Integration test fixtures that create temporary profiles SHALL use the directory-based layout (`profiles/<name>/profile.yaml`) matching the contract of `discover_profiles()`. Fixture profile dicts SHALL NOT contain `runtime.internet` or `runtime.timeout` fields.

#### Scenario: built_test_image fixture builds a discoverable profile
- **WHEN** the `built_test_image` module-scoped fixture runs
- **THEN** it copies `profiles/test/` into a temporary directory, runs `isolagent build test --force`, and verifies the `isolagent-test` volume exists in libvirt
- **AND** on teardown it deletes the `isolagent-test` volume

#### Scenario: Shared fixtures exclude removed fields
- **WHEN** `VALID_PROFILE` or `MINIMAL_PROFILE` fixtures are used in unit tests
- **THEN** they do not contain `internet` or `timeout` keys in the `runtime` section

#### Scenario: session_env fixture creates a patched profile for each test
- **WHEN** the `session_env` function-scoped fixture runs
- **THEN** it loads the `test` profile via `load_profile()`, patches `project.workdir` to a temporary git repo and `project.extra_syncs` to a temporary directory with a marker file
- **AND** it returns a dict with `profile`, `workdir`, `extra_sync_dir`, and `tmp_path`
