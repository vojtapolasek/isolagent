import copy
import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import VALID_PROFILE


def _libvirt_available():
    try:
        import libvirt

        conn = libvirt.open("qemu:///system")
        conn.close()
        return True
    except Exception:
        return False


def _iso_tool_available():
    return any(shutil.which(tool) for tool in ["xorrisofs", "genisoimage", "mkisofs"])


integration = pytest.mark.integration

requires_libvirt = pytest.mark.skipif(not _libvirt_available(), reason="libvirtd not reachable")

requires_iso_tool = pytest.mark.skipif(
    not _iso_tool_available(), reason="no ISO tool (genisoimage/mkisofs/xorrisofs) in PATH"
)


class TestSessionRunnerInit:
    def test_creates_runner_with_profile(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")
        assert runner.profile == profile
        assert runner.output_mode == "patch"

    def test_default_output_dir_is_none(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")
        assert runner.output_dir is None

    def test_custom_output_dir(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="sync", output_dir="/tmp/out")
        assert runner.output_dir == "/tmp/out"

    def test_shell_mode(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, shell=True)
        assert runner.shell is True
        assert runner.output_mode is None

    def test_initial_state_has_libvirt_fields(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")
        assert runner.conn is None
        assert runner.domain is None
        assert runner.domain_name is None
        assert runner.overlay_vol_name is None
        assert runner.guest_ip is None
        assert runner.socat_lock_fd is None

    def test_has_phase_methods(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")
        assert callable(runner.init)
        assert callable(runner.setup)
        assert callable(runner.run)
        assert callable(runner.teardown)


class TestNewPreflight:
    def test_missing_image_raises(self, monkeypatch):
        from isolagent.session import SessionError, SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")

        mock_conn = MagicMock()
        mock_pool = MagicMock()

        with (
            patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.libvirt_helpers.check_default_network"),
            patch("isolagent.libvirt_helpers.get_default_pool", return_value=mock_pool),
            patch("isolagent.libvirt_helpers.volume_exists", return_value=False),
            pytest.raises(SessionError, match="Base image volume"),
        ):
            runner.preflight()

    def test_missing_iso_tool_raises(self, monkeypatch):
        from isolagent.session import SessionError, SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")

        mock_conn = MagicMock()

        monkeypatch.setattr("shutil.which", lambda cmd: None)

        with (
            patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.libvirt_helpers.check_default_network"),
            patch("isolagent.libvirt_helpers.get_default_pool"),
            patch("isolagent.libvirt_helpers.volume_exists", return_value=True),
            pytest.raises(SessionError, match="No ISO creation tool found"),
        ):
            runner.preflight()

    def test_preflight_calls_libvirt_helpers(self, monkeypatch, tmp_path):
        import subprocess

        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["project"]["workdir"] = str(tmp_path / "proj")
        runner = SessionRunner(profile, output_mode="patch")

        proj = tmp_path / "proj"
        proj.mkdir(parents=True)
        subprocess.run(["git", "init", str(proj)], capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "init"],
            capture_output=True,
            check=True,
            cwd=str(proj),
        )

        mock_conn = MagicMock()
        calls = []

        def fake_get_conn(prof=None):
            calls.append("get_conn")
            return mock_conn

        def fake_check_network(conn):
            calls.append("check_network")

        def fake_get_pool(conn):
            calls.append("get_pool")
            return MagicMock()

        def fake_volume_exists(conn, name):
            calls.append(f"volume_exists:{name}")
            return True

        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/genisoimage")

        with (
            patch("isolagent.libvirt_helpers.get_libvirt_connection", fake_get_conn),
            patch("isolagent.libvirt_helpers.check_default_network", fake_check_network),
            patch("isolagent.libvirt_helpers.get_default_pool", fake_get_pool),
            patch("isolagent.libvirt_helpers.volume_exists", fake_volume_exists),
        ):
            runner.preflight()

        assert "get_conn" in calls
        assert "check_network" in calls
        assert "get_pool" in calls
        assert "volume_exists:isolagent-test-profile" in calls


class TestPatchModeGitPreflight:
    def _make_runner(self, tmp_path, monkeypatch, output_mode="patch"):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["project"]["workdir"] = str(tmp_path / "proj")
        runner = SessionRunner(profile, output_mode=output_mode)
        runner.project_root = tmp_path

        mock_conn = MagicMock()
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/genisoimage")

        with (
            patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.libvirt_helpers.check_default_network"),
            patch("isolagent.libvirt_helpers.get_default_pool"),
            patch("isolagent.libvirt_helpers.volume_exists", return_value=True),
        ):
            pass

        return runner

    def test_not_git_repo_raises(self, tmp_path, monkeypatch):
        from isolagent.session import SessionError

        runner = self._make_runner(tmp_path, monkeypatch)
        proj = Path(runner.profile["project"]["workdir"])
        proj.mkdir(parents=True)

        mock_conn = MagicMock()
        with (
            patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.libvirt_helpers.check_default_network"),
            patch("isolagent.libvirt_helpers.get_default_pool"),
            patch("isolagent.libvirt_helpers.volume_exists", return_value=True),
            pytest.raises(SessionError, match="not a git repository"),
        ):
            runner.preflight()

    def test_empty_repo_no_commits_raises(self, tmp_path, monkeypatch):
        import subprocess

        from isolagent.session import SessionError

        runner = self._make_runner(tmp_path, monkeypatch)
        proj = Path(runner.profile["project"]["workdir"])
        proj.mkdir(parents=True)
        subprocess.run(["git", "init", str(proj)], capture_output=True, check=True)

        mock_conn = MagicMock()
        with (
            patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.libvirt_helpers.check_default_network"),
            patch("isolagent.libvirt_helpers.get_default_pool"),
            patch("isolagent.libvirt_helpers.volume_exists", return_value=True),
            pytest.raises(SessionError, match="has no commits"),
        ):
            runner.preflight()

    def test_valid_git_repo_passes(self, tmp_path, monkeypatch):
        import subprocess

        runner = self._make_runner(tmp_path, monkeypatch)
        proj = Path(runner.profile["project"]["workdir"])
        proj.mkdir(parents=True)
        subprocess.run(["git", "init", str(proj)], capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "init"],
            capture_output=True,
            check=True,
            cwd=str(proj),
        )

        mock_conn = MagicMock()
        with (
            patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.libvirt_helpers.check_default_network"),
            patch("isolagent.libvirt_helpers.get_default_pool"),
            patch("isolagent.libvirt_helpers.volume_exists", return_value=True),
        ):
            runner.preflight()

    def test_sync_mode_skips_git_check(self, tmp_path, monkeypatch):
        runner = self._make_runner(tmp_path, monkeypatch, output_mode="sync")
        proj = Path(runner.profile["project"]["workdir"])
        proj.mkdir(parents=True)

        mock_conn = MagicMock()
        with (
            patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.libvirt_helpers.check_default_network"),
            patch("isolagent.libvirt_helpers.get_default_pool"),
            patch("isolagent.libvirt_helpers.volume_exists", return_value=True),
        ):
            runner.preflight()

    def test_none_mode_skips_git_check(self, tmp_path, monkeypatch):
        runner = self._make_runner(tmp_path, monkeypatch, output_mode="none")
        proj = Path(runner.profile["project"]["workdir"])
        proj.mkdir(parents=True)

        mock_conn = MagicMock()
        with (
            patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.libvirt_helpers.check_default_network"),
            patch("isolagent.libvirt_helpers.get_default_pool"),
            patch("isolagent.libvirt_helpers.volume_exists", return_value=True),
        ):
            runner.preflight()


class TestSSHHelpers:
    def test_ssh_cmd_base_includes_options(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")
        runner.guest_ip = "192.168.122.50"
        cmd = runner._ssh_cmd_base()
        assert "ssh" in cmd
        assert "-o" in cmd
        assert "StrictHostKeyChecking=no" in " ".join(cmd)
        assert "UserKnownHostsFile=/dev/null" in " ".join(cmd)

    def test_ssh_cmd_base_has_no_key_flag(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")
        runner.guest_ip = "192.168.122.50"
        cmd = runner._ssh_cmd_base()
        assert "-i" not in cmd

    def test_ssh_cmd_base_includes_identities_only(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")
        runner.guest_ip = "192.168.122.50"
        cmd = runner._ssh_cmd_base()
        assert "IdentitiesOnly=yes" in " ".join(cmd)

    def test_ssh_cmd_base_targets_guest_ip(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")
        runner.guest_ip = "192.168.122.50"
        cmd = runner._ssh_cmd_base()
        assert "root@192.168.122.50" in cmd


class TestRsyncHelper:
    def test_rsync_to_guest_command(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")
        runner.guest_ip = "192.168.122.50"
        cmd = runner._rsync_cmd("/host/path/", "root@192.168.122.50:/isolagent/project/")
        assert "rsync" in cmd
        assert "--delete" in cmd
        assert "--chown=root:root" in cmd
        assert "/host/path/" in cmd
        assert "root@192.168.122.50:/isolagent/project/" in cmd


class TestExtraSyncsCollisionDetection:
    def test_duplicate_basenames_raises(self):
        from isolagent.session import SessionError, SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["project"]["extra_syncs"] = ["/home/user/a/data", "/home/user/b/data"]
        runner = SessionRunner(profile, output_mode="patch")
        with pytest.raises(SessionError, match="data"):
            runner._validate_extra_syncs()

    def test_collision_with_project_raises(self):
        from isolagent.session import SessionError, SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["project"]["extra_syncs"] = ["/home/user/project"]
        runner = SessionRunner(profile, output_mode="patch")
        with pytest.raises(SessionError, match="project"):
            runner._validate_extra_syncs()

    def test_no_collision_passes(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["project"]["extra_syncs"] = ["/home/user/data", "/home/user/tools"]
        runner = SessionRunner(profile, output_mode="patch")
        runner._validate_extra_syncs()


class TestProjectSync:
    def test_sync_commands_for_workdir(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")
        runner.guest_ip = "192.168.122.50"
        cmds = runner._sync_in_commands()
        assert len(cmds) >= 1
        cmd_str = " ".join(cmds[0])
        assert "/tmp/test-project/" in cmd_str
        assert "/isolagent/project/" in cmd_str

    def test_sync_commands_for_extra_syncs(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["project"]["extra_syncs"] = [
            "/home/user/data",
            "/home/user/tools",
        ]
        runner = SessionRunner(profile, output_mode="patch")
        runner.guest_ip = "192.168.122.50"
        cmds = runner._sync_in_commands()
        assert len(cmds) == 3
        assert "/isolagent/data/" in " ".join(cmds[1])
        assert "/isolagent/tools/" in " ".join(cmds[2])


class TestGuestFiles:
    def test_guest_files_commands_walks_tree(self, tmp_path):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["_profile_dir"] = str(tmp_path / "myprofile")
        guest_files = tmp_path / "myprofile" / "guest-files" / "root" / ".claude"
        guest_files.mkdir(parents=True)
        (guest_files / "settings.json").write_text('{"key": "val"}')
        ssh_dir = tmp_path / "myprofile" / "guest-files" / "root" / ".ssh"
        ssh_dir.mkdir(parents=True)
        (ssh_dir / "config").write_text("Host *\n")

        runner = SessionRunner(profile, output_mode="patch")
        cmds = runner._guest_file_commands()
        assert len(cmds) == 2
        destinations = {cmd["guest_path"] for cmd in cmds}
        assert "/root/.claude/settings.json" in destinations
        assert "/root/.ssh/config" in destinations

    def test_guest_files_no_directory(self, tmp_path):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["_profile_dir"] = str(tmp_path / "myprofile")
        (tmp_path / "myprofile").mkdir()

        runner = SessionRunner(profile, output_mode="patch")
        cmds = runner._guest_file_commands()
        assert cmds == []

    def test_guest_files_creates_parent_dirs(self, tmp_path):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["_profile_dir"] = str(tmp_path / "myprofile")
        nested = tmp_path / "myprofile" / "guest-files" / "opt" / "app" / "conf"
        nested.mkdir(parents=True)
        (nested / "app.cfg").write_text("config")

        runner = SessionRunner(profile, output_mode="patch")
        cmds = runner._guest_file_commands()
        assert len(cmds) == 1
        assert cmds[0]["guest_path"] == "/opt/app/conf/app.cfg"
        assert cmds[0]["host_path"].endswith("app.cfg")


class TestAgentCommand:
    def test_agent_env_cmd(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["agent"]["env"] = {"FOO": "bar", "BAZ": "qux"}
        profile["agent"]["command"] = "claude --dangerously-skip-permissions"
        runner = SessionRunner(profile, output_mode="patch")
        cmd = runner._agent_tmux_cmd()
        assert "env " in cmd
        assert "FOO=bar" in cmd
        assert "BAZ=qux" in cmd
        assert "claude --dangerously-skip-permissions" in cmd
        cd_pos = cmd.index("cd ")
        env_pos = cmd.index("env ")
        assert cd_pos < env_pos, f"env must wrap agent command after cd, got: {cmd}"

    def test_agent_env_cmd_empty(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["agent"]["env"] = {}
        profile["agent"]["command"] = "claude --dangerously-skip-permissions"
        runner = SessionRunner(profile, output_mode="patch")
        cmd = runner._agent_tmux_cmd()
        assert "env " not in cmd
        assert "claude --dangerously-skip-permissions" in cmd

    def test_agent_env_cmd_quotes_special_chars(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["agent"]["env"] = {"MSG": "hello world"}
        profile["agent"]["command"] = "echo test"
        runner = SessionRunner(profile, output_mode="patch")
        cmd = runner._agent_tmux_cmd()
        assert "MSG=" in cmd
        assert "hello world" in cmd

    def test_agent_cmd_includes_cd(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["agent"]["command"] = "echo hello"
        runner = SessionRunner(profile, output_mode="patch")
        cmd = runner._agent_tmux_cmd()
        assert "cd /isolagent/project" in cmd

    def test_shell_cmd_includes_env(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["agent"]["env"] = {"FOO": "bar", "BAZ": "qux"}
        runner = SessionRunner(profile, shell=True)
        cmd = runner._shell_cmd()
        assert "env " in cmd
        assert "FOO=bar" in cmd
        assert "BAZ=qux" in cmd
        assert cmd.endswith("bash")

    def test_shell_cmd_no_env(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["agent"]["env"] = {}
        runner = SessionRunner(profile, shell=True)
        cmd = runner._shell_cmd()
        assert "env " not in cmd
        assert "cd /isolagent/project" in cmd
        assert cmd.endswith("bash")

    def test_shell_cmd_quotes_special_chars(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["agent"]["env"] = {"MSG": "hello world"}
        runner = SessionRunner(profile, shell=True)
        cmd = runner._shell_cmd()
        assert "MSG=" in cmd
        assert "hello world" in cmd


class TestCloudInitISO:
    def test_network_config_uses_dhcp(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")
        runner.domain_name = "isolagent-test-abc123"
        network_cfg = runner._cloud_init_network_config()
        assert "dhcp4: true" in network_cfg
        assert "version: 2" in network_cfg

    def test_meta_data_contains_domain_name(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")
        runner.domain_name = "isolagent-test-abc123"
        meta = runner._cloud_init_meta_data()
        assert "isolagent-isolagent-test-abc123" in meta

    def test_iso_cmd_uses_discovered_tool(self, tmp_path):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")
        runner.iso_tool = "xorrisofs"
        cidata_dir = tmp_path / "cidata"
        cidata_dir.mkdir()
        iso_path = tmp_path / "cidata.iso"
        cmd = runner._iso_cmd(str(cidata_dir), str(iso_path))
        assert "xorrisofs" in cmd
        assert str(iso_path) in cmd
        assert "cidata" in " ".join(cmd)

    def test_user_data_preserves_root_access(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")
        user_data = runner._cloud_init_user_data()

        assert "disable_root: false" in user_data
        assert "lock_passwd: false" in user_data

    def test_user_data_has_no_ssh_keys(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")
        user_data = runner._cloud_init_user_data()

        assert "ssh_authorized_keys" not in user_data
        assert "PermitRootLogin" not in user_data


class TestSocatStart:
    def test_socat_cmd_for_libvirt(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")
        cmd = runner._socat_cmd()
        assert "socat" in cmd
        assert "VSOCK-LISTEN:16509" in " ".join(cmd)
        assert "libvirt" in " ".join(cmd)


class TestSocatLockTimeout:
    def test_flock_raises_after_timeout(self, tmp_path):
        import fcntl

        from isolagent.session import SessionError, SessionRunner

        pid_path = tmp_path / "socat.pid"
        held_fd = os.open(str(pid_path), os.O_RDWR | os.O_CREAT)
        fcntl.flock(held_fd, fcntl.LOCK_EX)

        try:
            profile = copy.deepcopy(VALID_PROFILE)
            runner = SessionRunner(profile, output_mode="patch")

            with (
                patch.object(runner, "_socat_dir", return_value=tmp_path),
                pytest.raises(SessionError, match="lock.*timed out"),
            ):
                runner._start_socat_with_flock(timeout=1)
        finally:
            os.close(held_fd)


class TestOutputExtraction:
    def test_patch_cmd_uses_initial_head(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")
        runner.initial_head = "abc123"
        cmd = runner._patch_format_cmd()
        assert "git format-patch" in cmd
        assert "abc123" in cmd

    def test_patch_output_path_default(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="patch")
        path = runner._patch_output_path()
        assert path.startswith("/tmp/test-project/")
        assert "isolagent-" in path
        assert path.endswith(".patch")

    def test_patch_output_path_custom_dir(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(
            profile,
            output_mode="patch",
            output_dir="/tmp/out",
        )
        path = runner._patch_output_path()
        assert path.startswith("/tmp/out/")

    def test_sync_out_command_default(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="sync")
        runner.guest_ip = "192.168.122.50"
        cmd = runner._sync_out_cmd()
        cmd_str = " ".join(cmd)
        assert "/isolagent/project/" in cmd_str
        assert "/tmp/test-project/" in cmd_str

    def test_sync_out_command_custom_dir(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(
            profile,
            output_mode="sync",
            output_dir="/tmp/out",
        )
        runner.guest_ip = "192.168.122.50"
        cmd = runner._sync_out_cmd()
        cmd_str = " ".join(cmd)
        assert "/tmp/out/" in cmd_str

    def test_sync_out_always_uses_delete(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="sync")
        runner.guest_ip = "192.168.122.50"
        cmd = runner._sync_out_cmd()
        assert "--delete" in cmd

    def test_sync_out_delete_when_different_dir(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(
            profile,
            output_mode="sync",
            output_dir="/tmp/other",
        )
        runner.guest_ip = "192.168.122.50"
        cmd = runner._sync_out_cmd()
        assert "--delete" in cmd


class TestNoneOutputModeSkipsSSH:
    def test_none_mode_does_not_ssh(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="none")
        runner.guest_ip = "192.168.122.50"

        ssh_calls = []
        original_ssh_run = runner._ssh_run

        def tracking_ssh_run(cmd, **kwargs):
            ssh_calls.append(cmd)
            return original_ssh_run(cmd, **kwargs)

        runner._ssh_run = tracking_ssh_run
        runner._extract_output()

        assert ssh_calls == [], (
            "_extract_output with mode 'none' should not SSH,"
            f" but called _ssh_run with: {ssh_calls}"
        )

    def test_none_mode_prints_discard_message(self, capsys):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="none")
        runner.guest_ip = "192.168.122.50"

        runner._extract_output()

        captured = capsys.readouterr()
        assert "none" in captured.out.lower()
        assert "discard" in captured.out.lower()


class TestOutputDirPreflight:
    def test_nonexistent_output_dir_raises(self, tmp_path, monkeypatch):
        from isolagent.session import SessionError, SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(
            profile,
            output_mode="patch",
            output_dir=str(tmp_path / "nonexistent"),
        )

        mock_conn = MagicMock()
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/genisoimage")

        with (
            patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.libvirt_helpers.check_default_network"),
            patch("isolagent.libvirt_helpers.get_default_pool"),
            patch("isolagent.libvirt_helpers.volume_exists", return_value=True),
            pytest.raises(SessionError, match="does not exist"),
        ):
            runner.preflight()

    def test_non_writable_output_dir_raises(self, tmp_path, monkeypatch):
        from isolagent.session import SessionError, SessionRunner

        out_dir = tmp_path / "readonly"
        out_dir.mkdir()
        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(
            profile,
            output_mode="patch",
            output_dir=str(out_dir),
        )

        monkeypatch.setattr("os.access", lambda p, m: False)
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/genisoimage")

        mock_conn = MagicMock()
        with (
            patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.libvirt_helpers.check_default_network"),
            patch("isolagent.libvirt_helpers.get_default_pool"),
            patch("isolagent.libvirt_helpers.volume_exists", return_value=True),
            pytest.raises(SessionError, match="not writable"),
        ):
            runner.preflight()

    def test_sync_non_empty_dir_without_overwrite_raises(self, tmp_path, monkeypatch):
        from isolagent.session import SessionError, SessionRunner

        out_dir = tmp_path / "output"
        out_dir.mkdir()
        (out_dir / "existing.txt").write_text("data")
        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(
            profile,
            output_mode="sync",
            output_dir=str(out_dir),
            overwrite=False,
        )

        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/genisoimage")

        mock_conn = MagicMock()
        with (
            patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.libvirt_helpers.check_default_network"),
            patch("isolagent.libvirt_helpers.get_default_pool"),
            patch("isolagent.libvirt_helpers.volume_exists", return_value=True),
            pytest.raises(SessionError, match="not empty"),
        ):
            runner.preflight()

    def test_sync_non_empty_dir_with_overwrite_passes(self, tmp_path, monkeypatch):
        from isolagent.session import SessionRunner

        out_dir = tmp_path / "output"
        out_dir.mkdir()
        (out_dir / "existing.txt").write_text("data")
        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(
            profile,
            output_mode="sync",
            output_dir=str(out_dir),
            overwrite=True,
        )

        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/genisoimage")

        mock_conn = MagicMock()
        with (
            patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.libvirt_helpers.check_default_network"),
            patch("isolagent.libvirt_helpers.get_default_pool"),
            patch("isolagent.libvirt_helpers.volume_exists", return_value=True),
        ):
            runner.preflight()

    def test_sync_empty_dir_without_overwrite_passes(self, tmp_path, monkeypatch):
        from isolagent.session import SessionRunner

        out_dir = tmp_path / "output"
        out_dir.mkdir()
        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(
            profile,
            output_mode="sync",
            output_dir=str(out_dir),
            overwrite=False,
        )

        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/genisoimage")

        mock_conn = MagicMock()
        with (
            patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.libvirt_helpers.check_default_network"),
            patch("isolagent.libvirt_helpers.get_default_pool"),
            patch("isolagent.libvirt_helpers.volume_exists", return_value=True),
        ):
            runner.preflight()

    def test_no_output_dir_skips_check(self, tmp_path, monkeypatch):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(
            profile,
            output_mode="sync",
            output_dir=None,
        )

        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/genisoimage")

        mock_conn = MagicMock()
        with (
            patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.libvirt_helpers.check_default_network"),
            patch("isolagent.libvirt_helpers.get_default_pool"),
            patch("isolagent.libvirt_helpers.volume_exists", return_value=True),
        ):
            runner.preflight()


class TestInitPhase:
    def test_init_starts_socat_when_libvirt_access(self, tmp_path):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["runtime"]["access_host_libvirt"] = True
        runner = SessionRunner(profile, output_mode="patch")
        runner.iso_tool = "genisoimage"

        mock_conn = MagicMock()
        runner.conn = mock_conn

        socat_calls = []

        def fake_start_socat():
            socat_calls.append("started")
            runner.socat_lock_fd = 42

        with (
            patch(
                "isolagent.libvirt_helpers.generate_domain_name",
                return_value="isolagent-test-abc123",
            ),
            patch("isolagent.libvirt_helpers.create_overlay_volume"),
            patch("subprocess.run"),
        ):
            runner._start_socat_with_flock = fake_start_socat
            runner.init()

        assert len(socat_calls) == 1
        assert runner.socat_lock_fd == 42

    def test_init_skips_socat_when_no_libvirt_access(self, tmp_path):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["runtime"]["access_host_libvirt"] = False
        runner = SessionRunner(profile, output_mode="patch")
        runner.iso_tool = "genisoimage"

        mock_conn = MagicMock()
        runner.conn = mock_conn

        socat_calls = []

        def fake_start_socat():
            socat_calls.append("started")

        with (
            patch(
                "isolagent.libvirt_helpers.generate_domain_name",
                return_value="isolagent-test-abc123",
            ),
            patch("isolagent.libvirt_helpers.create_overlay_volume"),
            patch("subprocess.run"),
        ):
            runner._start_socat_with_flock = fake_start_socat
            runner.init()

        assert len(socat_calls) == 0


@integration
@requires_libvirt
@requires_iso_tool
class TestInitPhaseIntegration:
    def _create_dummy_base_volume(self, conn, name):
        pool = conn.storagePoolLookupByName("default")
        vol_xml = f"""<volume>
  <name>{name}</name>
  <capacity unit='bytes'>1048576</capacity>
  <target><format type='qcow2'/></target>
</volume>"""
        return pool.createXML(vol_xml, 0)

    def _cleanup_volume(self, conn, name):
        try:
            pool = conn.storagePoolLookupByName("default")
            vol = pool.storageVolLookupByName(name)
            vol.delete(0)
        except Exception:
            pass

    def _find_iso_tool(self):
        for tool in ["xorrisofs", "genisoimage", "mkisofs"]:
            if shutil.which(tool):
                return tool
        return None

    def test_init_creates_overlay_volume(self):
        from isolagent.libvirt_helpers import (
            generate_domain_name,
            get_libvirt_connection,
            volume_exists,
        )
        from isolagent.session import SessionRunner

        suffix = generate_domain_name("test-init")
        profile_name = suffix
        base_vol_name = f"isolagent-{profile_name}"

        profile = copy.deepcopy(VALID_PROFILE)
        profile["name"] = profile_name

        conn = get_libvirt_connection()
        self._create_dummy_base_volume(conn, base_vol_name)
        try:
            runner = SessionRunner(profile, output_mode="patch")
            runner.conn = conn
            runner.iso_tool = self._find_iso_tool()
            runner.init()

            assert runner.overlay_vol_name is not None
            assert volume_exists(conn, runner.overlay_vol_name)

            pool = conn.storagePoolLookupByName("default")
            overlay_vol = pool.storageVolLookupByName(runner.overlay_vol_name)
            overlay_xml = overlay_vol.XMLDesc(0)
            root = ET.fromstring(overlay_xml)
            backing = root.find(".//backingStore/path")
            assert backing is not None
            assert base_vol_name in backing.text
        finally:
            if runner.overlay_vol_name:
                self._cleanup_volume(conn, runner.overlay_vol_name)
            self._cleanup_volume(conn, base_vol_name)
            if runner.cidata_dir and runner.cidata_dir.exists():
                shutil.rmtree(runner.cidata_dir)
            if runner.cidata_iso and runner.cidata_iso.exists():
                runner.cidata_iso.unlink()
            conn.close()

    def test_init_creates_cloud_init_iso(self):
        from isolagent.libvirt_helpers import (
            generate_domain_name,
            get_libvirt_connection,
        )
        from isolagent.session import SessionRunner

        suffix = generate_domain_name("test-iso")
        profile_name = suffix
        base_vol_name = f"isolagent-{profile_name}"

        profile = copy.deepcopy(VALID_PROFILE)
        profile["name"] = profile_name

        conn = get_libvirt_connection()
        self._create_dummy_base_volume(conn, base_vol_name)
        try:
            runner = SessionRunner(profile, output_mode="patch")
            runner.conn = conn
            runner.iso_tool = self._find_iso_tool()
            runner.init()

            assert runner.cidata_iso is not None
            assert runner.cidata_iso.exists()
            assert runner.cidata_dir is not None
            assert (runner.cidata_dir / "meta-data").exists()
            assert (runner.cidata_dir / "user-data").exists()
            assert (runner.cidata_dir / "network-config").exists()
        finally:
            if runner.overlay_vol_name:
                self._cleanup_volume(conn, runner.overlay_vol_name)
            self._cleanup_volume(conn, base_vol_name)
            if runner.cidata_dir and runner.cidata_dir.exists():
                shutil.rmtree(runner.cidata_dir)
            if runner.cidata_iso and runner.cidata_iso.exists():
                runner.cidata_iso.unlink()
            conn.close()


class TestTeardown:
    def test_teardown_idempotent(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="none")
        runner.teardown()
        runner.teardown()

    def test_teardown_destroys_domain(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="none")

        mock_domain = MagicMock()
        runner.domain = mock_domain

        with patch("isolagent.libvirt_helpers.destroy_domain") as mock_destroy:
            runner.teardown()

        mock_destroy.assert_called_once_with(mock_domain)

    def test_teardown_deletes_overlay_volume(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="none")

        mock_conn = MagicMock()
        runner.conn = mock_conn
        runner.overlay_vol_name = "isolagent-test-abc123-overlay"

        with patch("isolagent.libvirt_helpers.delete_volume") as mock_delete:
            runner.teardown()

        mock_delete.assert_called_once_with(mock_conn, "isolagent-test-abc123-overlay")

    def test_teardown_cleans_cidata(self, tmp_path):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="none")
        cidata_dir = tmp_path / "cidata"
        cidata_dir.mkdir()
        cidata_iso = tmp_path / "cidata.iso"
        cidata_iso.touch()
        runner.cidata_dir = cidata_dir
        runner.cidata_iso = cidata_iso
        runner.teardown()
        assert not cidata_dir.exists()
        assert not cidata_iso.exists()

    def test_teardown_cleans_console_log(self, tmp_path):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="none")
        log = tmp_path / "console.log"
        log.touch()
        runner.console_log = log
        runner.teardown()
        assert not log.exists()

    def test_teardown_shell_skips_extraction(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, shell=True)
        runner.teardown()

    def test_teardown_prints_extraction_error(self, capsys, monkeypatch):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="sync")
        monkeypatch.setattr(
            "isolagent.session.SessionRunner._extract_output",
            lambda self: (_ for _ in ()).throw(RuntimeError("disk full")),
        )
        runner.teardown()
        captured = capsys.readouterr()
        assert "disk full" in captured.err

    def test_teardown_stops_socat_when_libvirt(self):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        profile["runtime"]["access_host_libvirt"] = True
        runner = SessionRunner(profile, output_mode="none")

        stop_calls = []

        def fake_stop():
            stop_calls.append("stopped")

        runner._stop_socat_with_flock = fake_stop
        runner.teardown()

        assert len(stop_calls) == 1


@integration
@requires_libvirt
class TestTeardownIntegration:
    def _create_dummy_volume(self, conn, name):
        pool = conn.storagePoolLookupByName("default")
        vol_xml = f"""<volume>
  <name>{name}</name>
  <capacity unit='bytes'>1048576</capacity>
  <target><format type='qcow2'/></target>
</volume>"""
        return pool.createXML(vol_xml, 0)

    def test_teardown_deletes_overlay_volume(self):
        from isolagent.libvirt_helpers import (
            create_overlay_volume,
            generate_domain_name,
            get_libvirt_connection,
            volume_exists,
        )
        from isolagent.session import SessionRunner

        base_name = generate_domain_name("test-td-base")
        overlay_name = generate_domain_name("test-td-overlay")

        profile = copy.deepcopy(VALID_PROFILE)
        conn = get_libvirt_connection()
        try:
            self._create_dummy_volume(conn, base_name)
            create_overlay_volume(conn, overlay_name, base_name)
            assert volume_exists(conn, overlay_name)

            runner = SessionRunner(profile, output_mode="none")
            runner.conn = conn
            runner.overlay_vol_name = overlay_name
            runner.teardown()

            verify_conn = get_libvirt_connection()
            try:
                assert not volume_exists(verify_conn, overlay_name)
            finally:
                verify_conn.close()
        finally:
            cleanup_conn = get_libvirt_connection()
            for name in (overlay_name, base_name):
                try:
                    pool = cleanup_conn.storagePoolLookupByName("default")
                    vol = pool.storageVolLookupByName(name)
                    vol.delete(0)
                except Exception:
                    pass
            cleanup_conn.close()


class TestCmdRunWiring:
    def test_cmd_run_calls_lifecycle_phases(self, monkeypatch):
        from isolagent.cli import cmd_run

        calls = []
        mock_runner = MagicMock()
        mock_runner.preflight = lambda: calls.append("preflight")
        mock_runner.init = lambda: calls.append("init")
        mock_runner.setup = lambda: calls.append("setup")
        mock_runner.run = lambda: calls.append("run")
        mock_runner.teardown = lambda: calls.append("teardown")

        def mock_session_cls(*a, **kw):
            return mock_runner

        args = MagicMock()
        args.profile = "test-profile"
        args.profiles_dir = None
        args.output_mode = "patch"
        args.output_dir = None
        args.shell = False
        args.memory = None
        args.cpus = None

        with (
            patch("isolagent.cli.load_profile") as mock_load,
            patch("isolagent.cli.SessionRunner", mock_session_cls),
        ):
            mock_load.return_value = copy.deepcopy(VALID_PROFILE)
            cmd_run(args)

        assert calls == [
            "preflight",
            "init",
            "setup",
            "run",
            "teardown",
        ]

    def test_cmd_run_teardown_on_error(self, monkeypatch):
        from isolagent.cli import cmd_run

        calls = []
        mock_runner = MagicMock()
        mock_runner.preflight = lambda: calls.append("preflight")
        mock_runner.init = lambda: calls.append("init")

        def failing_setup():
            calls.append("setup")
            raise RuntimeError("boom")

        mock_runner.setup = failing_setup
        mock_runner.run = lambda: calls.append("run")
        mock_runner.teardown = lambda: calls.append("teardown")

        def mock_session_cls(*a, **kw):
            return mock_runner

        args = MagicMock()
        args.profile = "test-profile"
        args.profiles_dir = None
        args.output_mode = "patch"
        args.output_dir = None
        args.shell = False
        args.memory = None
        args.cpus = None

        with (
            patch("isolagent.cli.load_profile") as mock_load,
            patch("isolagent.cli.SessionRunner", mock_session_cls),
        ):
            mock_load.return_value = copy.deepcopy(VALID_PROFILE)
            with pytest.raises(RuntimeError):
                cmd_run(args)

        assert "teardown" in calls
        assert "run" not in calls

    def test_cmd_run_passes_output_args(self, monkeypatch):
        from isolagent.cli import cmd_run

        captured = {}

        def mock_session_cls(profile, **kw):
            captured.update(kw)
            runner = MagicMock()
            return runner

        args = MagicMock()
        args.profile = "test-profile"
        args.profiles_dir = None
        args.output_mode = "sync"
        args.output_dir = "/tmp/out"
        args.shell = False
        args.memory = None
        args.cpus = None
        args.overwrite = True

        with (
            patch("isolagent.cli.load_profile") as mock_load,
            patch("isolagent.cli.SessionRunner", mock_session_cls),
        ):
            mock_load.return_value = copy.deepcopy(VALID_PROFILE)
            cmd_run(args)

        assert captured["output_mode"] == "sync"
        assert captured["output_dir"] == "/tmp/out"
        assert captured["overwrite"] is True
        assert captured["shell"] is False


class TestReconnectLoop:
    def test_breaks_immediately_on_tmux_session_gone(self, monkeypatch):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="none")
        runner.guest_ip = "192.168.122.50"

        call_log = []

        def mock_run(cmd, **kwargs):
            result = MagicMock()
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            call_log.append(cmd_str)
            if "tmux new-session" in cmd_str:
                result.returncode = 0
            elif "tmux has-session" in cmd_str:
                result.returncode = 1
            elif "tmux attach-session" in cmd_str:
                result.returncode = 0
            else:
                result.returncode = 0
            return result

        monkeypatch.setattr("subprocess.run", mock_run)
        runner.run()

        has_session_calls = [c for c in call_log if "has-session" in c]
        assert len(has_session_calls) == 1, (
            f"Expected 1 has-session call (immediate break), got {len(has_session_calls)}"
        )

    def test_retries_on_ssh_transport_failure(self, monkeypatch):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="none")
        runner.guest_ip = "192.168.122.50"

        has_session_count = 0

        def mock_run(cmd, **kwargs):
            nonlocal has_session_count
            result = MagicMock()
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            if "tmux new-session" in cmd_str:
                result.returncode = 0
            elif "tmux has-session" in cmd_str:
                has_session_count += 1
                result.returncode = 255
            elif "tmux attach-session" in cmd_str:
                result.returncode = 0
            else:
                result.returncode = 0
            return result

        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr("time.sleep", lambda s: None)
        runner.run()

        assert has_session_count == 10, (
            f"Expected 10 retries for SSH failure (255), got {has_session_count}"
        )

    def test_recovers_after_transient_ssh_failure(self, monkeypatch):
        from isolagent.session import SessionRunner

        profile = copy.deepcopy(VALID_PROFILE)
        runner = SessionRunner(profile, output_mode="none")
        runner.guest_ip = "192.168.122.50"

        has_session_count = 0
        call_log = []

        def mock_run(cmd, **kwargs):
            nonlocal has_session_count
            result = MagicMock()
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            call_log.append(cmd_str)
            if "tmux new-session" in cmd_str:
                result.returncode = 0
            elif "tmux has-session" in cmd_str:
                has_session_count += 1
                if has_session_count <= 2:
                    result.returncode = 255
                elif has_session_count == 3:
                    result.returncode = 0
                else:
                    result.returncode = 1
            elif "tmux attach-session" in cmd_str:
                result.returncode = 0
            else:
                result.returncode = 0
            return result

        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr("time.sleep", lambda s: None)
        runner.run()

        assert has_session_count == 4
        attach_calls = [c for c in call_log if "attach-session" in c]
        assert len(attach_calls) == 1


class TestCmdList:
    def test_shows_active_sessions_table(self, capsys, monkeypatch):
        from isolagent.cli import cmd_list

        mock_conn = MagicMock()
        mock_domain1 = MagicMock()
        mock_domain1.name.return_value = "isolagent-test-abc123"
        mock_domain1.state.return_value = (1, 0)
        mock_domain1.XMLDesc.return_value = """
<domain>
  <metadata>
    <isolagent:profile xmlns:isolagent="http://isolagent.local/">test-profile</isolagent:profile>
  </metadata>
</domain>
"""
        mock_domain1.interfaceAddresses.return_value = {
            "vnet0": {"addrs": [{"type": 0, "addr": "192.168.122.50"}]}
        }

        mock_conn.listAllDomains.return_value = [mock_domain1]

        with (
            patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn),
        ):
            cmd_list(None)

        output = capsys.readouterr().out
        assert "Domain" in output
        assert "Profile" in output
        assert "isolagent-test-abc123" in output
        assert "192.168.122.50" in output

    def test_prints_no_active_sessions(self, capsys, monkeypatch):
        from isolagent.cli import cmd_list

        mock_conn = MagicMock()
        mock_conn.listAllDomains.return_value = []

        with (
            patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn),
        ):
            cmd_list(None)

        output = capsys.readouterr().out
        assert "No active sessions" in output

    def test_run_no_slot_argument(self):
        from isolagent.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["run", "myprofile", "--output-mode", "patch"])
        assert not hasattr(args, "slot")
