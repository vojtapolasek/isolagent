import copy
from unittest.mock import MagicMock, patch

import pytest
import yaml

BUILDER_PROFILE = {
    "name": "test-build",
    "image": {
        "os": "fedora",
        "roles": ["agent-claude"],
    },
    "agent": {
        "command": "echo run",
    },
    "project": {
        "workdir": "/tmp/test-project",
    },
}


@pytest.fixture
def builder_profile():
    return copy.deepcopy(BUILDER_PROFILE)


class TestRoleAssembly:
    def test_basic_roles(self, builder_profile):
        from isolagent.builder import assemble_roles

        roles = assemble_roles(builder_profile)
        assert roles == ["base", "fedora", "agent-claude"]

    def test_with_libvirt(self, builder_profile):
        from isolagent.builder import assemble_roles

        builder_profile["runtime"] = {"access_host_libvirt": True}
        roles = assemble_roles(builder_profile)
        assert roles == ["base", "fedora", "libvirt-bridge", "agent-claude"]

    def test_without_libvirt(self, builder_profile):
        from isolagent.builder import assemble_roles

        builder_profile["runtime"] = {"access_host_libvirt": False}
        roles = assemble_roles(builder_profile)
        assert "libvirt-bridge" not in roles

    def test_multiple_profile_roles(self, builder_profile):
        from isolagent.builder import assemble_roles

        builder_profile["image"]["roles"] = ["agent-claude", "my-custom-role"]
        roles = assemble_roles(builder_profile)
        assert roles == ["base", "fedora", "agent-claude", "my-custom-role"]

    def test_empty_roles(self, builder_profile):
        from isolagent.builder import assemble_roles

        builder_profile["image"]["roles"] = []
        roles = assemble_roles(builder_profile)
        assert roles == ["base", "fedora"]

    def test_no_runtime_section(self, builder_profile):
        from isolagent.builder import assemble_roles

        builder_profile.pop("runtime", None)
        roles = assemble_roles(builder_profile)
        assert "libvirt-bridge" not in roles


class TestPlaybookGeneration:
    def test_generates_valid_yaml(self, builder_profile):
        from isolagent.builder import assemble_roles, generate_playbook

        roles = assemble_roles(builder_profile)
        content = generate_playbook(roles)
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["hosts"] == "all"
        assert parsed[0]["become"] is True

    def test_roles_in_order(self, builder_profile):
        from isolagent.builder import assemble_roles, generate_playbook

        roles = assemble_roles(builder_profile)
        content = generate_playbook(roles)
        parsed = yaml.safe_load(content)
        assert parsed[0]["roles"] == ["base", "fedora", "agent-claude"]


class TestRolesPath:
    def test_includes_global_roles(self, builder_profile, tmp_path):
        from isolagent.builder import _build_roles_path

        roles_dir = tmp_path / "roles"
        roles_dir.mkdir()
        path = _build_roles_path(builder_profile, roles_dir=roles_dir)
        assert str(roles_dir) in path

    def test_includes_profile_local_roles(self, builder_profile, tmp_path):
        from isolagent.builder import _build_roles_path

        roles_dir = tmp_path / "roles"
        roles_dir.mkdir()
        profile_dir = tmp_path / "profiles" / "test"
        profile_roles = profile_dir / "roles"
        profile_roles.mkdir(parents=True)
        builder_profile["_profile_dir"] = str(profile_dir)

        path = _build_roles_path(builder_profile, roles_dir=roles_dir)
        parts = path.split(":")
        assert str(profile_roles) == parts[0]
        assert str(roles_dir) == parts[1]

    def test_profile_local_first(self, builder_profile, tmp_path):
        from isolagent.builder import _build_roles_path

        roles_dir = tmp_path / "roles"
        roles_dir.mkdir()
        profile_dir = tmp_path / "profiles" / "test"
        profile_roles = profile_dir / "roles"
        profile_roles.mkdir(parents=True)
        builder_profile["_profile_dir"] = str(profile_dir)

        path = _build_roles_path(builder_profile, roles_dir=roles_dir)
        parts = path.split(":")
        assert parts[0] == str(profile_roles)

    def test_no_profile_dir(self, builder_profile, tmp_path):
        from isolagent.builder import _build_roles_path

        roles_dir = tmp_path / "roles"
        roles_dir.mkdir()
        builder_profile.pop("_profile_dir", None)

        path = _build_roles_path(builder_profile, roles_dir=roles_dir)
        assert path == str(roles_dir)




class TestPreflightChecks:
    def test_missing_libvirt_raises(self, monkeypatch):
        from isolagent.builder import check_preflight
        from isolagent.session import SessionError

        def fake_get_conn(profile=None):
            raise SessionError("libvirt not available")

        with (
            patch("isolagent.builder.get_libvirt_connection", fake_get_conn),
            pytest.raises(SystemExit),
        ):
            check_preflight()

    def test_missing_ansible_raises(self, monkeypatch):
        from isolagent.builder import check_preflight

        mock_conn = MagicMock()

        def fake_which(cmd):
            if cmd == "ansible-playbook":
                return None
            return f"/usr/bin/{cmd}"

        monkeypatch.setattr("shutil.which", fake_which)

        with (
            patch("isolagent.builder.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.builder.check_default_network"),
            patch("isolagent.builder.get_default_pool"),pytest.raises(SystemExit)
        ):
            check_preflight()

    def test_missing_kvm_raises(self, monkeypatch, tmp_path):
        from isolagent.builder import check_preflight

        mock_conn = MagicMock()

        def fake_which(cmd):
            return f"/usr/bin/{cmd}"

        monkeypatch.setattr("shutil.which", fake_which)
        monkeypatch.setattr("isolagent.builder.KVM_DEVICE", str(tmp_path / "nonexistent"))

        with (
            patch("isolagent.builder.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.builder.check_default_network"),
            patch("isolagent.builder.get_default_pool"),pytest.raises(SystemExit)
        ):
            check_preflight()

    def test_all_present_passes(self, monkeypatch, tmp_path):
        from isolagent.builder import check_preflight

        mock_conn = MagicMock()

        def fake_which(cmd):
            return f"/usr/bin/{cmd}"

        monkeypatch.setattr("shutil.which", fake_which)
        kvm = tmp_path / "kvm"
        kvm.touch()
        monkeypatch.setattr("isolagent.builder.KVM_DEVICE", str(kvm))

        with (
            patch("isolagent.builder.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.builder.check_default_network"),
            patch("isolagent.builder.get_default_pool"),
        ):
            check_preflight()

    def test_profile_passed_to_libvirt_connection(self, monkeypatch, tmp_path):
        from isolagent.builder import check_preflight

        mock_conn = MagicMock()
        profile = {"runtime": {"libvirt_uri": "qemu:///session"}}
        received = {}

        def fake_get_conn(p=None):
            received["profile"] = p
            return mock_conn

        def fake_which(cmd):
            return f"/usr/bin/{cmd}"

        monkeypatch.setattr("shutil.which", fake_which)
        kvm = tmp_path / "kvm"
        kvm.touch()
        monkeypatch.setattr("isolagent.builder.KVM_DEVICE", str(kvm))

        with (
            patch("isolagent.builder.get_libvirt_connection", fake_get_conn),
            patch("isolagent.builder.check_default_network"),
            patch("isolagent.builder.get_default_pool"),
        ):
            check_preflight(profile)

        assert received["profile"] is profile


class TestBaseImageDownload:
    def test_downloads_when_not_cached(self, tmp_path, monkeypatch):
        from isolagent.builder import download_base_image

        downloads_dir = tmp_path / "downloads"

        calls = []

        def fake_urlretrieve(url, path, reporthook=None):
            calls.append((url, path))
            with open(path, "w") as f:
                f.write("fake image")
            return path, {}

        monkeypatch.setattr("isolagent.builder.urlretrieve", fake_urlretrieve)
        result = download_base_image(
            "https://example.com/fedora.qcow2", downloads_dir=downloads_dir,
        )
        assert result.exists()
        assert len(calls) == 1

    def test_skips_when_cached(self, tmp_path, monkeypatch):
        from isolagent.builder import download_base_image

        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir(parents=True)
        cached = downloads_dir / "fedora.qcow2"
        cached.write_text("cached image")

        calls = []

        def fake_urlretrieve(url, path, reporthook=None):
            calls.append((url, path))

        monkeypatch.setattr("isolagent.builder.urlretrieve", fake_urlretrieve)
        result = download_base_image(
            "https://example.com/fedora.qcow2", downloads_dir=downloads_dir,
        )
        assert result == cached
        assert len(calls) == 0

    def test_sha256_match_fresh_download(self, tmp_path, monkeypatch):
        import hashlib

        from isolagent.builder import download_base_image

        content = b"test image content"
        expected_hash = hashlib.sha256(content).hexdigest()
        downloads_dir = tmp_path / "downloads"

        def fake_urlretrieve(url, path, reporthook=None):
            with open(path, "wb") as f:
                f.write(content)

        monkeypatch.setattr("isolagent.builder.urlretrieve", fake_urlretrieve)
        result = download_base_image(
            "https://example.com/fedora.qcow2", sha256=expected_hash, downloads_dir=downloads_dir
        )
        assert result.exists()

    def test_sha256_mismatch_fresh_download_raises(self, tmp_path, monkeypatch):
        from isolagent.builder import DownloadError, download_base_image

        downloads_dir = tmp_path / "downloads"

        def fake_urlretrieve(url, path, reporthook=None):
            with open(path, "w") as f:
                f.write("corrupt data")

        monkeypatch.setattr("isolagent.builder.urlretrieve", fake_urlretrieve)
        with pytest.raises(DownloadError, match="SHA-256 mismatch"):
            download_base_image(
                "https://example.com/fedora.qcow2", sha256="a" * 64, downloads_dir=downloads_dir
            )
        assert not (downloads_dir / "fedora.qcow2").exists()

    def test_sha256_match_cached(self, tmp_path, monkeypatch):
        import hashlib

        from isolagent.builder import download_base_image

        content = b"cached image content"
        expected_hash = hashlib.sha256(content).hexdigest()
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir(parents=True)
        cached = downloads_dir / "fedora.qcow2"
        cached.write_bytes(content)

        calls = []
        monkeypatch.setattr(
            "isolagent.builder.urlretrieve",
            lambda url, path, reporthook=None: calls.append(url),
        )
        result = download_base_image(
            "https://example.com/fedora.qcow2", sha256=expected_hash, downloads_dir=downloads_dir
        )
        assert result == cached
        assert len(calls) == 0

    def test_sha256_mismatch_cached_redownloads(self, tmp_path, monkeypatch):
        import hashlib

        from isolagent.builder import download_base_image

        good_content = b"good image"
        expected_hash = hashlib.sha256(good_content).hexdigest()
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir(parents=True)
        cached = downloads_dir / "fedora.qcow2"
        cached.write_bytes(b"corrupt cached data")

        def fake_urlretrieve(url, path, reporthook=None):
            with open(path, "wb") as f:
                f.write(good_content)

        monkeypatch.setattr("isolagent.builder.urlretrieve", fake_urlretrieve)
        result = download_base_image(
            "https://example.com/fedora.qcow2", sha256=expected_hash, downloads_dir=downloads_dir
        )
        assert result.exists()
        assert result.read_bytes() == good_content

    def test_no_sha256_skips_verification(self, tmp_path, monkeypatch):
        from isolagent.builder import download_base_image

        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir(parents=True)
        cached = downloads_dir / "fedora.qcow2"
        cached.write_text("any content")

        result = download_base_image(
            "https://example.com/fedora.qcow2", downloads_dir=downloads_dir,
        )
        assert result == cached

    def test_custom_downloads_dir(self, tmp_path, monkeypatch):
        from isolagent.builder import download_base_image

        custom_dir = tmp_path / "custom"

        def fake_urlretrieve(url, path, reporthook=None):
            with open(path, "w") as f:
                f.write("image")

        monkeypatch.setattr("isolagent.builder.urlretrieve", fake_urlretrieve)
        result = download_base_image(
            "https://example.com/fedora.qcow2", downloads_dir=custom_dir
        )
        assert result.parent == custom_dir
        assert result.exists()


class TestRebuildProtection:
    def test_detects_existing_image(self, tmp_path):
        from isolagent.builder import image_exists

        mock_conn = MagicMock()

        with (
            patch("isolagent.builder.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.builder.volume_exists", return_value=True),
        ):
            assert image_exists("test-profile") is True

    def test_no_existing_image(self, tmp_path):
        from isolagent.builder import image_exists

        mock_conn = MagicMock()

        with (
            patch("isolagent.builder.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.builder.volume_exists", return_value=False),
        ):
            assert image_exists("test-profile") is False


class TestRunBuildLibvirtBased:
    def test_build_calls_ansible(self, monkeypatch, tmp_path):
        from isolagent.builder import run_build

        mock_conn = MagicMock()
        mock_domain = MagicMock()

        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            result = MagicMock()
            result.returncode = 0
            return result

        monkeypatch.setattr("subprocess.run", fake_run)
        monkeypatch.setattr("isolagent.builder.check_preflight", lambda profile=None: None)
        monkeypatch.setattr("isolagent.builder.image_exists", lambda name: False)
        monkeypatch.setattr(
            "isolagent.profile.load_os_role_vars",
            lambda os_name: {"base_image_url": "https://example.com/fedora.qcow2"},
        )

        cached = tmp_path / "fedora.qcow2"
        cached.write_bytes(b"fake image")
        monkeypatch.setattr("isolagent.builder.download_base_image", lambda *a, **kw: cached)

        with (
            patch("isolagent.builder.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.builder.upload_volume"),
            patch("isolagent.builder.generate_domain_name", return_value="isolagent-test-abc123"),
            patch(
                "isolagent.builder.get_volume_path",
                return_value="/var/lib/libvirt/images/isolagent-test.qcow2",
            ),
            patch("isolagent.builder.cleanup_stale_domain"),
            patch("isolagent.builder.create_domain", return_value=mock_domain),
            patch("isolagent.builder.discover_guest_ip", return_value="192.168.122.50"),
            patch("isolagent.builder.destroy_domain"),
        ):
            run_build(BUILDER_PROFILE, force=False)

        ansible_calls = [c for c in calls if "ansible-playbook" in str(c)]
        assert len(ansible_calls) > 0

    def test_build_cleans_up_on_failure(self, monkeypatch, tmp_path):
        from isolagent.builder import run_build

        mock_conn = MagicMock()
        mock_domain = MagicMock()

        call_count = [0]

        def fake_run(cmd, **kwargs):
            call_count[0] += 1
            if call_count[0] > 1:
                raise RuntimeError("build failed")
            result = MagicMock()
            result.returncode = 0
            return result

        monkeypatch.setattr("subprocess.run", fake_run)
        monkeypatch.setattr("isolagent.builder.check_preflight", lambda profile=None: None)
        monkeypatch.setattr("isolagent.builder.image_exists", lambda name: False)
        monkeypatch.setattr(
            "isolagent.profile.load_os_role_vars",
            lambda os_name: {"base_image_url": "https://example.com/fedora.qcow2"},
        )

        cached = tmp_path / "fedora.qcow2"
        cached.write_bytes(b"fake image")
        monkeypatch.setattr("isolagent.builder.download_base_image", lambda *a, **kw: cached)

        with (
            patch("isolagent.builder.get_libvirt_connection", return_value=mock_conn),
            patch("isolagent.builder.upload_volume"),
            patch("isolagent.builder.generate_domain_name", return_value="isolagent-test-abc123"),
            patch(
                "isolagent.builder.get_volume_path",
                return_value="/var/lib/libvirt/images/isolagent-test.qcow2",
            ),
            patch("isolagent.builder.cleanup_stale_domain"),
            patch("isolagent.builder.create_domain", return_value=mock_domain),
            patch("isolagent.builder.discover_guest_ip", return_value="192.168.122.50"),
            patch("isolagent.builder.destroy_domain") as mock_destroy,
            patch("isolagent.builder.delete_volume") as mock_delete,
            pytest.raises(SystemExit),
        ):
            run_build(BUILDER_PROFILE, force=False)

        mock_destroy.assert_called_once_with(mock_domain)
        mock_delete.assert_called_once_with(mock_conn, "isolagent-test-build")
