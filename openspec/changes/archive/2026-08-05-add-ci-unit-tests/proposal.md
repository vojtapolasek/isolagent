## Why

The project has no automated CI. Unit tests (`pytest`, default markers exclude `integration`/`slow`) and lint (`ruff`) must currently be run manually, so regressions or style issues can land on `main` or in a PR unnoticed.

## What Changes

- Add a GitHub Actions workflow (`.github/workflows/ci.yml`) with two independent jobs:
  - `test`: installs the project (`pip install -e ".[dev]"`) and runs the unit-tier test suite (bare `pytest`, per `docs/testing.md`).
  - `lint`: installs `ruff` only and runs `ruff check`.
- Trigger both jobs on pushes to `main` and on pull requests targeting `main`.
- Cancel superseded in-progress runs for the same ref (`concurrency` group) to avoid wasting runner time on rapid follow-up pushes.
- Add a CI status badge to `README.md` linking to the workflow's Actions page.
- Integration and slow tests (marked `integration`/`slow`) are out of scope — they require KVM/libvirt/Ansible and are not suited to a standard hosted runner.

## Capabilities

No spec-level product behavior changes — this is CI/tooling only. `skip_specs: true` is set in `.openspec.yaml`.

## Impact

- New file: `.github/workflows/ci.yml`.
- `README.md`: one badge line added near the top.
- No changes to `isolagent` source, CLI behavior, or profile schema.
- No new runtime dependencies; `pyproject.toml`'s existing `dev` extra (`pytest`, `ruff`) is reused. `libvirt-python` (a hard dependency of the package, needed only by the `test` job) requires system libvirt headers to build from source on the runner — the `test` job installs `libvirt-dev`/`pkg-config` via `apt-get` before `pip install`. The `lint` job needs neither, since `ruff` performs static analysis without importing the package.
