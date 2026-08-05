## Context

`docs/testing.md` defines three test tiers. Bare `pytest` (unit tier) needs only Python and `pip install -e ".[dev]"` — no KVM/libvirt/Ansible. `pyproject.toml` already sets `addopts = "-m 'not integration and not slow'"`, so a bare `pytest` invocation is sufficient to select the unit tier; no extra marker flags are needed in the workflow.

`libvirt-python` is a hard runtime dependency (`pyproject.toml`). It ships as a source distribution on PyPI (no prebuilt wheels for standard Linux runners), so building it requires the libvirt C headers and `pkg-config` to be present before `pip install` runs. `ruff` (also in the `dev` extra) performs static analysis only and never imports `isolagent` or its dependencies, so it doesn't need the package installed at all.

## Goals / Non-Goals

**Goals:**
- Unit tests and lint run automatically on every push to `main` and every pull request targeting `main`, on a standard GitHub-hosted runner (no KVM/libvirt/Ansible available).
- Fast feedback: minimal installs per job, no unnecessary matrix legs, superseded runs cancelled automatically.

**Non-Goals:**
- Running integration or slow tests (they require KVM/libvirt/Ansible/sshpass and a built VM image — not available on hosted runners and out of scope per the proposal).
- Coverage reporting or badges.
- `ruff format --check` — only `ruff check` (lint) was requested; formatting enforcement can be a follow-up change.

## Decisions

- **Workflow file**: single file `.github/workflows/ci.yml`, `name: CI`, with two independent jobs: `test` and `lint`. They share the same triggers and are conceptually "the checks that gate a PR," but need different install steps — GitHub Actions jobs are independent by design, so this doesn't require separate files. PR checks show as `CI / test` and `CI / lint`.
- **Triggers**: `push` to `branches: [main]` and `pull_request` to `branches: [main]`, applied at the workflow level (shared by both jobs). Matches the request literally and avoids redundant runs on feature-branch pushes that already have an open PR, or PRs targeting non-`main` branches.
- **Concurrency**: a workflow-level `concurrency` group keyed on workflow name + ref, with `cancel-in-progress: true`, so a new push to the same branch/PR cancels the previous run instead of letting both finish.
- **Runner**: `ubuntu-latest` for both jobs — cheapest hosted option, sufficient since neither job needs virtualization.
- **Python version**: single version, `3.14` (current stable, within the project's `requires-python = ">=3.10"`). A version matrix is easy to add later (one line, `strategy.matrix.python-version`) if the project needs to guarantee compatibility across 3.10–3.14; not justified yet for a single-maintainer project with no evidence of version-specific bugs.
- **`test` job steps**: `apt-get install -y libvirt-dev pkg-config` (build prerequisite for `libvirt-python`) → `pip install -e ".[dev]"` (matches `AGENTS.md`'s documented build/test command exactly) → bare `pytest` (relies on the existing `addopts` marker exclusion rather than repeating `-m "not integration and not slow"` in the workflow, so the two stay in sync by construction).
- **`lint` job steps**: `pip install ruff` (no apt-get, no project install — matches the unbounded `ruff>=0.11` constraint in `pyproject.toml`'s dev extra) → `ruff check .`.
- **Caching**: `actions/setup-python`'s built-in `cache: pip` in both jobs, keyed by `pyproject.toml`.
- **README badge**: single badge for the `CI` workflow (GitHub Actions badges reflect overall workflow status, i.e. worst of its jobs — one badge is enough since `test` and `lint` are both part of the same `ci.yml`). Placed directly under the `# isolagent` title, above the existing `> **Status:**` line, using the standard `https://github.com/<owner>/<repo>/actions/workflows/ci.yml/badge.svg` badge linking to the workflow's Actions page.

## Risks / Trade-offs

- [Single Python version misses version-specific breakage] → Acceptable for now; upgrading to a matrix later is a one-line `strategy.matrix` addition, not a redesign.
- [`apt-get install libvirt-dev` adds ~10-20s to the `test` job] → Necessary; without it `pip install` fails outright since `libvirt-python` has no wheel to fall back to. Not paid by the `lint` job.
- [Restricting `pull_request` to `branches: [main]` skips PRs opened against other base branches] → Acceptable; this repo's contribution flow targets `main` (per README).
