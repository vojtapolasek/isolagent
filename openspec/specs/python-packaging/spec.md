## Requirements

### Requirement: Package metadata and Python version
The project SHALL be packaged as `isolagent` version `0.1.0` using setuptools. It SHALL require Python >= 3.10.

#### Scenario: Install with compatible Python
- **WHEN** `pip install -e .` is run on Python 3.10+
- **THEN** the package installs successfully

#### Scenario: Install with incompatible Python
- **WHEN** `pip install -e .` is run on Python < 3.10
- **THEN** the install fails with a version constraint error

### Requirement: Runtime dependencies
The project SHALL declare three runtime dependencies: `pyyaml>=6.0`, `jsonschema>=4.0`, and `libvirt-python>=10.0`.

#### Scenario: Dependencies installed
- **WHEN** the package is installed
- **THEN** pyyaml, jsonschema, and libvirt-python are available at their minimum versions

### Requirement: Dev dependencies
The project SHALL declare optional dev dependencies under `[project.optional-dependencies] dev`: `pytest>=8.0` and `ruff>=0.11`.

#### Scenario: Dev install
- **WHEN** `pip install -e '.[dev]'` is run
- **THEN** pytest and ruff are installed alongside runtime dependencies

### Requirement: Console entry point
The project SHALL expose a single console script `isolagent` that maps to `isolagent.cli:main`.

#### Scenario: CLI available after install
- **WHEN** the package is installed
- **THEN** `isolagent --help` is available on the PATH

### Requirement: Pytest configuration
The project SHALL configure pytest via `pyproject.toml` with `testpaths = ["tests"]` and default addopts that exclude `integration` and `slow` markers. Two custom markers SHALL be defined: `integration` (requires libvirt, ansible, and KVM) and `slow` (nested VM tests).

#### Scenario: Default test run
- **WHEN** `pytest` is run without marker flags
- **THEN** only unit tests run (integration and slow tests are excluded)

#### Scenario: Integration test run
- **WHEN** `pytest -m integration` is run
- **THEN** integration tests run (requiring libvirt and KVM)

### Requirement: Ruff linting configuration
The project SHALL configure ruff with `target-version = "py310"`, `line-length = 99`, and lint rules selecting `E`, `F`, `W`, `I`, `N`, `UP`, `B`, `A`, `SIM`, `TCH`.

#### Scenario: Lint check
- **WHEN** `ruff check .` is run
- **THEN** the selected rule categories are enforced with a 99-character line limit
