# Tasks

## 1. Size parsing and profile schema

- [x] 1.1 Generalize `_parse_memory` to `parse_size()` in `isolagent/libvirt_helpers.py` accepting `M`/`G`/`T` (update call sites and error message) and verify with unit tests in `tests/test_libvirt_helpers.py` covering M/G/T, malformed input, and existing memory strings
- [x] 1.2 Add `runtime.disk` to `isolagent/profile_schema.json` (string, default `"20G"`, pattern `^[1-9][0-9]*[MGT]$`), add `"disk": "20G"` to runtime defaults in `isolagent/profile.py`, and verify with profile unit tests: default applied when omitted, `"40G"` accepted, `"big"` and `"40"` rejected with a message naming the field
- [x] 1.3 Add `disk` to `profiles/reference/profile.yaml` with a comment documenting units and default, and verify `python -m pytest tests/ -k profile` passes (schema/reference validation test)
- [x] 1.4 Document the `disk` field in `docs/profiles.md` runtime section and verify the documented example matches the schema pattern

## 2. Overlay sizing and minimum-size enforcement

- [x] 2.1 Parameterize `create_overlay_volume(conn, name, backing_vol_name, capacity_bytes)` in `isolagent/libvirt_helpers.py` (remove hardcoded 20 GiB) and verify via updated unit test asserting the `<capacity>` in the volume XML
- [x] 2.2 Add a base-volume virtual-size probe helper in `isolagent/libvirt_helpers.py` (`vol.refresh()` + `vol.info()["capacity"]`, raising `SessionError` on failure/zero) and verify with unit tests mocking libvirt (success, zero capacity, libvirtError)
- [x] 2.3 In `session.py` init phase, resolve `runtime.disk` → bytes, check against the base probe, raise `SessionError` naming the minimum when smaller, and pass capacity to `create_overlay_volume`; verify with unit tests: overlay created with configured size, too-small value fails before any volume/domain creation, equal size succeeds
- [x] 2.4 Document session disk behavior in `docs/sessions.md` (overlay size from `runtime.disk`, root filesystem grows into it, minimum = base image virtual size, build-time disk ceiling note that images ship at upstream size ~5 GiB) and verify the doc renders and matches implemented error text

## 3. Filesystem growth via session cloud-init

- [x] 3.1 Add `growpart: {mode: auto, devices: ["/"]}` and `resize_rootfs: true` to `_cloud_init_user_data()` in `isolagent/session.py` and verify with a unit test asserting the rendered user-data content (and that SSH/sshd keys are still absent)

## 4. CLI `--disk` override

- [x] 4.1 Add `--disk` to the `run` subparser in `isolagent/cli.py` and apply it in `_apply_overrides()`, with malformed override values surfacing `SessionError` at session start; verify with CLI unit tests (override sets `runtime.disk`, absent flag keeps profile value) and `isolagent run --help` shows the flag
- [x] 4.2 Document `--disk` in `docs/sessions.md` alongside `--memory`/`--cpus` and verify the usage example matches parser behavior

## 5. Integration verification

- [x] 5.1 Add an integration test (libvirt/KVM tier, following `tests/test_integration.py` conventions) that runs a session with `--disk 8G`, SSHes into the guest, and asserts root filesystem total size ≥ 7 GiB; verify it passes on the integration host and guards the growpart/Btrfs growth chain

## Workflow follow-up

- Run the full suite (`python -m pytest`) and the integration tier before archiving; then archive the change (`/opsx-archive` or `openspec archive`).
