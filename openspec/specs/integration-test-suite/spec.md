### Requirement: Module-scoped image build with cleanup
The integration test suite SHALL build the test profile image once per module and delete it after all tests complete.

#### Scenario: Image built once
- **WHEN** the integration test module starts
- **THEN** `isolagent build test` runs once producing a qcow2 image
- **AND** subsequent tests reuse the built image without rebuilding

#### Scenario: Image cleaned up
- **WHEN** the integration test module finishes (all tests complete or fail)
- **THEN** the built image storage volume is deleted from the libvirt pool

### Requirement: Function-scoped sessions with dynamic path patching
Each integration test SHALL get its own session with dynamically patched paths for `project.workdir` and `project.extra_syncs`.

#### Scenario: Workdir is a temp directory
- **WHEN** a test session is created
- **THEN** `project.workdir` is patched to a temporary directory containing a git repo with known content

#### Scenario: Extra syncs is a temp directory
- **WHEN** a test session is created
- **THEN** `project.extra_syncs` contains at least one temporary directory with a marker file

### Requirement: Test results retrieved via SSH
After the agent script completes, the outer test SHALL SSH into the VM to fetch `/tmp/test-results.json` before teardown. SSH connections SHALL use empty-password authentication (the base role configures `PermitEmptyPasswords yes` and deletes root's password) without any key file. This is the single verification method for all tests regardless of output mode.

#### Scenario: Results fetched before teardown
- **WHEN** the agent script finishes inside the VM
- **THEN** the test SSHs in using passwordless auth to read `/tmp/test-results.json`
- **AND** asserts all checks passed

### Requirement: Output mode patch test
The test suite SHALL include a test that runs a full session with `output-mode=patch` and verifies a patch file is produced.

#### Scenario: Patch output produced
- **WHEN** a session runs with `output-mode=patch`
- **THEN** agent in-VM checks pass (verified via SSH)
- **AND** a patch file is produced containing the agent's file modifications

### Requirement: Output mode sync test
The test suite SHALL include a test that runs a full session with `output-mode=sync` and verifies files are synced back.

#### Scenario: Sync output produced
- **WHEN** a session runs with `output-mode=sync` and a separate `output_dir`
- **THEN** agent in-VM checks pass (verified via SSH)
- **AND** modified files are synced back to the output directory

### Requirement: Output mode none test
The test suite SHALL include a test that runs a full session with `output-mode=none` and verifies nothing is synced back.

#### Scenario: No output produced
- **WHEN** a session runs with `output-mode=none`
- **THEN** agent in-VM checks pass (verified via SSH)
- **AND** no output files or directories are created

### Requirement: Teardown verification test
The test suite SHALL include a dedicated test that lets teardown complete normally and verifies host-side cleanup.

#### Scenario: QEMU process terminated
- **WHEN** teardown completes
- **THEN** the QEMU process for the session is no longer running

#### Scenario: Overlay disk removed
- **WHEN** teardown completes
- **THEN** the ephemeral overlay storage volume is deleted from the libvirt pool

### Requirement: Libvirt session integration test
The test suite SHALL include a test that runs a session with `runtime.access_host_libvirt: true`. The skip condition changes from checking `br-isolagent` to checking whether socat and libvirtd are available.

#### Scenario: Libvirt session runs
- **WHEN** a session runs with `access_host_libvirt: true` and libvirtd is reachable
- **THEN** the session completes successfully with socat/vsock bridge started

#### Scenario: Socat cleaned up after libvirt session
- **WHEN** teardown completes for a session with `runtime.access_host_libvirt: true`
- **THEN** the socat shared lock is released (`socat_lock_fd` is None) — socat is only terminated if no other sessions hold a shared lock

#### Scenario: Test skipped without libvirtd
- **WHEN** libvirtd is not reachable
- **THEN** the libvirt session test is skipped

### Requirement: Old integration tests replaced
The rewritten test suite SHALL cover all functionality previously tested in `test_integration.py`, and the old file SHALL be replaced.

#### Scenario: Build coverage preserved
- **WHEN** the new suite runs
- **THEN** it tests that `isolagent build test` produces a bootable qcow2 image (previously `test_build_produces_qcow2` and `test_built_image_boots_and_ssh`)

#### Scenario: Session lifecycle coverage preserved
- **WHEN** the new suite runs
- **THEN** it tests the full session lifecycle including preflight, init, setup, run, and teardown (previously `test_full_lifecycle_patch_mode`)
