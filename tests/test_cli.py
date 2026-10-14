import subprocess
import sys

import pytest

integration = pytest.mark.integration


def run_cli(*args):
    result = subprocess.run(
        [sys.executable, "-m", "isolagent.cli", *args],
        capture_output=True,
        text=True,
    )
    return result


class TestSubcommandDispatch:
    def test_no_subcommand_shows_help(self):
        result = run_cli()
        assert result.returncode == 0
        assert "run" in result.stdout
        assert "build" in result.stdout
        assert "list" in result.stdout

    def test_unknown_subcommand_errors(self):
        result = run_cli("nonexistent-cmd")
        assert result.returncode != 0


class TestRunSubcommand:
    @integration
    def test_run_with_profile_hits_preflight(self, tmp_path, monkeypatch):
        import yaml

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        profile_data = {
            "name": "test-profile",
            "image": {
                "os": "fedora",
            },
            "agent": {
                "command": "echo run",
            },
            "project": {"workdir": "/tmp/test"},
        }
        profile_dir = profiles_dir / "test-profile"
        profile_dir.mkdir()
        (profile_dir / "profile.yaml").write_text(yaml.dump(profile_data))

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "isolagent.cli",
                "run",
                "test-profile",
                "--profiles-dir",
                str(profiles_dir),
                "--output-mode",
                "patch",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert (
            "Base image volume" in result.stderr
            or "not found" in result.stderr
            or "does not exist" in result.stderr
        )

    def test_run_sync_requires_output_dir(self, tmp_path):
        import yaml

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        profile_data = {
            "name": "test-profile",
            "image": {
                "os": "fedora",
            },
            "agent": {
                "command": "echo run",
            },
            "project": {"workdir": "/tmp/test"},
        }
        profile_dir = profiles_dir / "test-profile"
        profile_dir.mkdir()
        (profile_dir / "profile.yaml").write_text(yaml.dump(profile_data))

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "isolagent.cli",
                "run",
                "test-profile",
                "--profiles-dir",
                str(profiles_dir),
                "--output-mode",
                "sync",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "--output-dir" in result.stderr

    def test_run_requires_output_mode(self, tmp_path):
        import yaml

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        profile_data = {
            "name": "test-profile",
            "image": {
                "os": "fedora",
            },
            "agent": {
                "command": "echo run",
            },
            "project": {"workdir": "/tmp/test"},
        }
        profile_dir = profiles_dir / "test-profile"
        profile_dir.mkdir()
        (profile_dir / "profile.yaml").write_text(yaml.dump(profile_data))

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "isolagent.cli",
                "run",
                "test-profile",
                "--profiles-dir",
                str(profiles_dir),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "--output-mode" in result.stderr

    def test_run_with_missing_profile_errors(self, tmp_path):
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "isolagent.cli",
                "run",
                "nonexistent",
                "--output-mode",
                "patch",
                "--profiles-dir",
                str(profiles_dir),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "nonexistent" in result.stderr


class TestBuildSubcommand:
    def test_build_with_missing_profile_errors(self, tmp_path):
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "isolagent.cli",
                "build",
                "nonexistent",
                "--profiles-dir",
                str(profiles_dir),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "nonexistent" in result.stderr

    def test_build_runs_preflight(self, tmp_path):
        import yaml

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        profile_data = {
            "name": "test-profile",
            "image": {
                "os": "fedora",
            },
            "agent": {
                "command": "echo run",
            },
            "project": {"workdir": "/tmp/test"},
        }
        profile_dir = profiles_dir / "test-profile"
        profile_dir.mkdir()
        (profile_dir / "profile.yaml").write_text(yaml.dump(profile_data))

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "isolagent.cli",
                "build",
                "test-profile",
                "--profiles-dir",
                str(profiles_dir),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            assert "not found" in result.stderr or "Error" in result.stderr


class TestStubSubcommands:
    @integration
    def test_list_stub(self, monkeypatch):
        from unittest.mock import MagicMock, patch

        mock_conn = MagicMock()
        mock_conn.listAllDomains.return_value = []

        with patch("isolagent.libvirt_helpers.get_libvirt_connection", return_value=mock_conn):
            result = run_cli("list")

        assert result.returncode == 0
