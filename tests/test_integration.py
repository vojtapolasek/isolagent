"""Integration tests for the isolagent session lifecycle.

Builds the test profile image once per module, then runs function-scoped
sessions to verify output modes, in-VM checks, teardown, and libvirt
session behavior.

Requirements:
  - /dev/kvm
  - libvirtd running, user in libvirt group
  - ansible-playbook, sshpass
  - Fedora cloud image (auto-provisioned by integration_prerequisites)

Run with: pytest -m integration
"""

import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from isolagent.profile import load_profile
from isolagent.session import SessionRunner

PROJECT_ROOT = Path(__file__).parent.parent

requires_ansible = pytest.mark.skipif(
    not shutil.which("ansible-playbook"), reason="ansible-playbook not in PATH"
)
requires_kvm = pytest.mark.skipif(not os.path.exists("/dev/kvm"), reason="/dev/kvm not available")


def _libvirt_available():
    try:
        import libvirt

        conn = libvirt.open("qemu:///system")
        conn.close()
        return True
    except Exception:
        return False


requires_libvirt = pytest.mark.skipif(not _libvirt_available(), reason="libvirtd not reachable")

requires_socat = pytest.mark.skipif(not shutil.which("socat"), reason="socat not available")

integration = pytest.mark.integration

TEST_PROFILE_DIR = PROJECT_ROOT / "profiles" / "test"


def _cli_env():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def _ssh_fetch_results(runner):
    result = subprocess.run(
        runner._ssh_cmd_base() + ["cat /tmp/test-results.json"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def built_test_image(integration_prerequisites, tmp_path_factory):
    profiles_dir = tmp_path_factory.mktemp("integration-build") / "profiles"
    profiles_dir.mkdir()
    test_profile_dir = profiles_dir / "test"
    shutil.copytree(TEST_PROFILE_DIR, test_profile_dir)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "isolagent.cli",
            "build",
            "test",
            "--profiles-dir",
            str(profiles_dir),
            "--force",
        ],
        capture_output=True,
        text=True,
        env=_cli_env(),
        timeout=600,
    )
    assert result.returncode == 0, (
        f"Build failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

    from isolagent.libvirt_helpers import get_libvirt_connection, volume_exists

    conn = get_libvirt_connection()
    assert volume_exists(conn, "isolagent-test"), "Build did not create isolagent-test volume"
    conn.close()

    yield profiles_dir

    from isolagent.libvirt_helpers import delete_volume

    conn = get_libvirt_connection()
    delete_volume(conn, "isolagent-test")
    conn.close()


@pytest.fixture
def session_env(built_test_image, tmp_path):
    profiles_dir = built_test_image

    workdir = tmp_path / "project"
    workdir.mkdir()
    subprocess.run(["git", "init", str(workdir)], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", str(workdir), "config", "user.email", "test@test.com"],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(workdir), "config", "user.name", "Test"],
        capture_output=True,
        check=True,
    )
    (workdir / "README.md").write_text("test project\n")
    subprocess.run(["git", "-C", str(workdir), "add", "."], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", str(workdir), "commit", "-m", "init"],
        capture_output=True,
        check=True,
    )

    extra_sync_dir = tmp_path / "extra-test"
    extra_sync_dir.mkdir()
    (extra_sync_dir / "extra-marker.txt").write_text("extra-sync-ok\n")

    profile = load_profile("test", profiles_dir)
    profile["project"]["workdir"] = str(workdir)
    profile["project"]["extra_syncs"] = [str(extra_sync_dir)]
    profile["_profile_dir"] = str(TEST_PROFILE_DIR)

    return {
        "profile": profile,
        "workdir": workdir,
        "extra_sync_dir": extra_sync_dir,
        "tmp_path": tmp_path,
    }


@integration
@requires_ansible
@requires_kvm
@requires_libvirt
class TestBuildAndBoot:
    def test_build_produces_volume(self, built_test_image):
        from isolagent.libvirt_helpers import get_libvirt_connection, volume_exists

        conn = get_libvirt_connection()
        assert volume_exists(conn, "isolagent-test")
        conn.close()


@integration
@requires_ansible
@requires_kvm
@requires_libvirt
class TestOutputModes:
    def test_output_mode_patch(self, session_env, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        profile = copy.deepcopy(session_env["profile"])
        profile["runtime"]["access_host_libvirt"] = False

        runner = SessionRunner(
            profile,
            output_mode="patch",
            output_dir=str(output_dir),
        )

        runner.preflight()
        try:
            runner.init()
            runner.setup()
            runner.run()
            results = _ssh_fetch_results(runner)
        finally:
            runner.teardown()

        assert results is not None, "Failed to fetch test results from VM"
        assert results["all_passed"], (
            f"In-VM checks failed: {json.dumps(results['checks'], indent=2)}"
        )

        patches = list(output_dir.glob("isolagent-*.patch"))
        assert len(patches) == 1, f"Expected 1 patch file, found {len(patches)}"
        patch_content = patches[0].read_text()
        assert "agent: test modification" in patch_content

    def test_output_mode_sync(self, session_env, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        profile = copy.deepcopy(session_env["profile"])
        profile["runtime"]["access_host_libvirt"] = False

        runner = SessionRunner(
            profile,
            output_mode="sync",
            output_dir=str(output_dir),
        )

        runner.preflight()
        try:
            runner.init()
            runner.setup()
            runner.run()
            results = _ssh_fetch_results(runner)
        finally:
            runner.teardown()

        assert results is not None, "Failed to fetch test results from VM"
        assert results["all_passed"], (
            f"In-VM checks failed: {json.dumps(results['checks'], indent=2)}"
        )

        readme = output_dir / "README.md"
        assert readme.exists(), "README.md not synced back"
        assert "modified by agent" in readme.read_text()

    def test_output_mode_none(self, session_env, tmp_path):
        profile = copy.deepcopy(session_env["profile"])
        profile["runtime"]["access_host_libvirt"] = False

        output_dir = tmp_path / "output"

        runner = SessionRunner(
            profile,
            output_mode="none",
        )

        runner.preflight()
        try:
            runner.init()
            runner.setup()
            runner.run()
            results = _ssh_fetch_results(runner)
        finally:
            runner.teardown()

        assert results is not None, "Failed to fetch test results from VM"
        assert results["all_passed"], (
            f"In-VM checks failed: {json.dumps(results['checks'], indent=2)}"
        )

        assert not output_dir.exists(), "Output directory should not exist for mode=none"


@integration
@requires_ansible
@requires_kvm
@requires_libvirt
class TestTeardown:
    def test_teardown_cleanup(self, built_test_image, tmp_path):
        profiles_dir = built_test_image

        workdir = tmp_path / "project"
        workdir.mkdir()
        subprocess.run(["git", "init", str(workdir)], capture_output=True, check=True)
        subprocess.run(
            ["git", "-C", str(workdir), "config", "user.email", "test@test.com"],
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(workdir), "config", "user.name", "Test"],
            capture_output=True,
            check=True,
        )
        (workdir / "README.md").write_text("test\n")
        subprocess.run(["git", "-C", str(workdir), "add", "."], capture_output=True, check=True)
        subprocess.run(
            ["git", "-C", str(workdir), "commit", "-m", "init"],
            capture_output=True,
            check=True,
        )

        profile = load_profile("test", profiles_dir)
        profile["project"]["workdir"] = str(workdir)
        profile["agent"]["command"] = "echo done"
        profile["runtime"]["access_host_libvirt"] = False
        profile["_profile_dir"] = str(TEST_PROFILE_DIR)

        runner = SessionRunner(profile, output_mode="none")

        runner.preflight()
        runner.init()
        runner.setup()

        assert runner.domain is not None
        domain_name = runner.domain_name
        overlay_vol_name = runner.overlay_vol_name

        runner.run()
        runner.teardown()

        from isolagent.libvirt_helpers import get_libvirt_connection, volume_exists

        conn = get_libvirt_connection()

        try:
            conn.lookupByName(domain_name)
            raise AssertionError(f"Domain {domain_name} still exists after teardown")
        except Exception:
            pass

        assert not volume_exists(conn, overlay_vol_name), (
            f"Overlay volume {overlay_vol_name} still exists after teardown"
        )
        conn.close()


@integration
@requires_ansible
@requires_kvm
@requires_libvirt
@requires_socat
class TestLibvirtSession:
    def test_libvirt_session(self, session_env, tmp_path):
        profile = copy.deepcopy(session_env["profile"])
        profile["runtime"]["access_host_libvirt"] = True

        runner = SessionRunner(
            profile,
            output_mode="none",
        )

        runner.preflight()
        try:
            runner.init()
            runner.setup()

            assert runner.socat_lock_fd is not None, (
                "socat not started for access_host_libvirt session"
            )

            runner.run()
            results = _ssh_fetch_results(runner)
        finally:
            runner.teardown()

        assert results is not None, "Failed to fetch test results from VM"
        assert results["all_passed"], (
            f"In-VM checks failed: {json.dumps(results['checks'], indent=2)}"
        )

        assert runner.socat_lock_fd is None, "socat lock fd not released after teardown"


@integration
@requires_ansible
@requires_kvm
@requires_libvirt
class TestDiskSizing:
    def test_root_fs_grows_to_configured_disk(self, session_env):
        """Guards the overlay-capacity + growpart + btrfs resize chain.

        Equivalent of `isolagent run test --output-mode none --disk 8G`:
        the resolved runtime.disk must size the overlay and the guest root
        filesystem must grow into it.
        """
        profile = copy.deepcopy(session_env["profile"])
        profile["runtime"]["access_host_libvirt"] = False
        profile["runtime"]["disk"] = "8G"
        profile["agent"]["command"] = "echo done"

        runner = SessionRunner(profile, output_mode="none")

        runner.preflight()
        try:
            runner.init()
            runner.setup()
            runner.run()

            result = subprocess.run(
                runner._ssh_cmd_base() + ["df", "-B1", "--output=size", "/"],
                capture_output=True,
                text=True,
                timeout=30,
            )
        finally:
            runner.teardown()

        assert result.returncode == 0, f"df failed: {result.stderr}"
        size_bytes = int(result.stdout.strip().splitlines()[-1])
        assert size_bytes >= 7 * 1024**3, (
            f"Root filesystem is {size_bytes / 1024**3:.2f} GiB, expected >= 7 GiB with --disk 8G"
        )
