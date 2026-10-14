# Testing

The test suite has three tiers: unit, integration, and slow. Bare `pytest` runs only unit tests. Integration and slow tests require explicit opt-in and have hardware/software prerequisites.

## Running Tests

```shell
# Unit tests only (fast, no special requirements)
pytest

# Integration tests (needs KVM, libvirt, ansible, sshpass, built image)
pytest -m integration

# Slow tests (needs nested KVM support inside a VM)
pytest -m slow

# Integration + slow together
pytest -m "integration or slow"

# Everything (unit + integration + slow)
pytest -m ""

# Show why tests were skipped
pytest -m "" -rs
```

Running all tests with `-m ""` includes integration and slow tests. These auto-skip when their prerequisites are missing — use `-rs` to see skip reasons. Common skips:

| Skip reason | What to do |
|-------------|------------|
| `libvirtd not available` | Start libvirtd (`systemctl start libvirtd` or `systemctl --user start libvirtd`) |
| `/dev/kvm not available` | Enable hardware virtualization in BIOS |
| `sshpass not in PATH` | Install sshpass (`pacman -S sshpass` / `dnf install sshpass`) |
| `ansible-playbook not in PATH` | Install ansible (`pacman -S ansible` / `dnf install ansible-core`) |
| `no ISO tool ... in PATH` | Install one of: `genisoimage`, `mkisofs`, or `xorrisofs` |

## Test Tiers

### Unit Tests

Run by default with bare `pytest`. Require only Python and the project dependencies (`pip install -e ".[dev]"`). No KVM, no libvirt, no host setup.

| Test file | What it covers |
|-----------|---------------|
| `test_profile.py` | Profile loading, validation, defaults, path expansion |
| `test_cli.py` | CLI argument parsing, subcommand dispatch |
| `test_builder.py` | Playbook generation, cloud-init templates |
| `test_libvirt_helpers.py` | Domain XML generation, domain name generation |
| `test_session.py` | Session runner methods, rsync commands, preflight checks |

### Integration Tests

Marker: `integration`. Require hardware and libvirt setup. Each test class applies its own `skipif` markers for specific prerequisites:

| Prerequisite | How to get it |
|-------------|---------------|
| `/dev/kvm` | Enable hardware virtualization in BIOS |
| libvirtd running | `systemctl start libvirtd` or `systemctl --user start libvirtd` |
| `sshpass` in PATH | `dnf install sshpass` (Fedora) or `pacman -S sshpass` (Arch) |
| `ansible-playbook` in PATH | `dnf install ansible-core` (Fedora) or `pacman -S ansible` (Arch) |
| Built image volume | Run `isolagent build <profile>` |
| ISO tool (`genisoimage`, `mkisofs`, or `xorrisofs`) | Install one of these packages |

Integration tests have two sub-tiers:

**Mid-tier** — validate libvirt interactions without booting a VM. Fast (seconds), require only libvirtd:

| Test class | File | What it covers |
|-----------|------|---------------|
| `TestDomainXMLValidation` | `test_libvirt_helpers.py` | Domain XML accepted by QEMU driver (catches bus/device incompatibilities) |
| `TestStoragePoolVolumeManagement` | `test_libvirt_helpers.py` | Volume CRUD against the real default pool |
| `TestInitPhaseIntegration` | `test_session.py` | Overlay volume creation and cloud-init ISO generation with real libvirt |
| `TestTeardownIntegration` | `test_session.py` | Overlay volume cleanup via real libvirt |

**End-to-end** — full build, boot, agent run, and teardown. Slow (minutes), require all prerequisites:

| Test class | File | What it covers |
|-----------|------|---------------|
| `TestBuildAndBoot` | `test_integration.py` | Image build produces a libvirt volume |
| `TestOutputModes` | `test_integration.py` | Session lifecycle in patch/sync/none modes |
| `TestTeardown` | `test_integration.py` | Domain and overlay cleanup after a real session |
| `TestDiskSizing` | `test_integration.py` | Configured disk size reaches the guest root filesystem (growpart/resize chain) |
| `TestLibvirtSession` | `test_integration.py` | Host libvirt access via vsock bridge |

Tests auto-skip when prerequisites are missing. A skipped test means the prerequisite is unavailable, not that the test is broken.

### Slow Tests

Marker: `slow` (always combined with `integration`). Require nested KVM support — the integration test VM must itself support `/dev/kvm`. These tests boot nested VMs and verify actual network packet flow.

Slow tests take several minutes because they boot VMs, install packages, and verify network connectivity.

## Adding New Tests

Place new test files in `tests/`. Use the standard pytest markers:

```python
import pytest

integration = pytest.mark.integration
slow = pytest.mark.slow

@integration
class TestMyFeature:
    def test_something(self):
        ...

@slow
@integration
class TestMySlowFeature:
    def test_network_thing(self):
        ...
```

Unit tests (no marker) run by default. Integration and slow tests require the caller to opt in with `-m`.
