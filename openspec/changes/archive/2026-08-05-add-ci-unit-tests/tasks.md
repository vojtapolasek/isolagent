## 1. Workflow file

- [x] 1.1 Create `.github/workflows/ci.yml` with `name: CI`.
- [x] 1.2 Add workflow-level triggers: `push` to `branches: [main]` and `pull_request` to `branches: [main]`.
- [x] 1.3 Add workflow-level `concurrency` group (keyed on workflow + ref) with `cancel-in-progress: true`.

## 2. `test` job

- [x] 2.1 Add `test` job on `ubuntu-latest`.
- [x] 2.2 Checkout, then set up Python 3.14 via `actions/setup-python` with `cache: pip`.
- [x] 2.3 Install system build prerequisites: `sudo apt-get update && sudo apt-get install -y libvirt-dev pkg-config`.
- [x] 2.4 Install the project: `pip install -e ".[dev]"`.
- [x] 2.5 Run `pytest`.

## 3. `lint` job

- [x] 3.1 Add `lint` job on `ubuntu-latest`.
- [x] 3.2 Checkout, then set up Python 3.14 via `actions/setup-python` with `cache: pip`.
- [x] 3.3 Install `ruff` directly (no project install, no apt-get).
- [x] 3.4 Run `ruff check .`.

## 4. README badge

- [x] 4.1 Add a CI status badge to `README.md`, under the `# isolagent` title, linking to `.github/workflows/ci.yml`'s Actions page.

## 5. Verification

- [x] 5.1 Validate the workflow YAML (e.g. `actionlint` or a YAML parser) for syntax errors.
- [x] 5.2 Push the branch and confirm both `CI / test` and `CI / lint` runs appear and pass on GitHub.
