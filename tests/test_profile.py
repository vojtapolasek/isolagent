import pytest

from isolagent.profile import ProfileError, discover_profiles, load_profile, validate_profile


class TestSchemaValidation:
    def test_valid_complete_profile(self, valid_profile):
        validate_profile(valid_profile)

    def test_valid_minimal_profile(self, minimal_profile):
        validate_profile(minimal_profile)

    def test_missing_required_section_agent(self, valid_profile):
        del valid_profile["agent"]
        with pytest.raises(ProfileError, match="agent"):
            validate_profile(valid_profile)

    def test_missing_required_section_image(self, valid_profile):
        del valid_profile["image"]
        with pytest.raises(ProfileError, match="image"):
            validate_profile(valid_profile)

    def test_missing_required_section_project(self, valid_profile):
        del valid_profile["project"]
        with pytest.raises(ProfileError, match="project"):
            validate_profile(valid_profile)

    def test_missing_required_section_name(self, valid_profile):
        del valid_profile["name"]
        with pytest.raises(ProfileError, match="name"):
            validate_profile(valid_profile)

    def test_missing_required_field_os(self, valid_profile):
        del valid_profile["image"]["os"]
        with pytest.raises(ProfileError, match="os"):
            validate_profile(valid_profile)

    def test_missing_required_field_agent_command(self, valid_profile):
        del valid_profile["agent"]["command"]
        with pytest.raises(ProfileError, match="command"):
            validate_profile(valid_profile)

    def test_missing_required_field_workdir(self, valid_profile):
        del valid_profile["project"]["workdir"]
        with pytest.raises(ProfileError, match="workdir"):
            validate_profile(valid_profile)

    def test_cpus_type_mismatch(self, valid_profile):
        valid_profile["runtime"]["cpus"] = "not-a-number"
        with pytest.raises(ProfileError, match="cpus"):
            validate_profile(valid_profile)

    def test_disk_valid_value(self, valid_profile):
        valid_profile["runtime"]["disk"] = "40G"
        validate_profile(valid_profile)
        assert valid_profile["runtime"]["disk"] == "40G"

    def test_disk_invalid_value_no_unit_rejected(self, valid_profile):
        valid_profile["runtime"]["disk"] = "40"
        with pytest.raises(ProfileError, match="disk"):
            validate_profile(valid_profile)

    def test_disk_invalid_value_non_numeric_rejected(self, valid_profile):
        valid_profile["runtime"]["disk"] = "big"
        with pytest.raises(ProfileError, match="disk"):
            validate_profile(valid_profile)

    def test_libvirt_type_mismatch(self, valid_profile):
        valid_profile["runtime"]["access_host_libvirt"] = "yes"
        with pytest.raises(ProfileError, match="access_host_libvirt"):
            validate_profile(valid_profile)

    def test_agent_env_must_be_string_map(self, valid_profile):
        valid_profile["agent"]["env"] = {"KEY": 123}
        with pytest.raises(ProfileError):
            validate_profile(valid_profile)

    def test_extra_syncs_must_be_list(self, valid_profile):
        valid_profile["project"]["extra_syncs"] = "/single/path"
        with pytest.raises(ProfileError):
            validate_profile(valid_profile)

    def test_workdir_with_extra_syncs(self, valid_profile):
        valid_profile["project"]["workdir"] = "/tmp/main"
        valid_profile["project"]["extra_syncs"] = ["/path/a", "/path/b"]
        validate_profile(valid_profile)
        assert valid_profile["project"]["workdir"] == "/tmp/main"
        assert valid_profile["project"]["extra_syncs"] == ["/path/a", "/path/b"]

    def test_roles_must_be_list(self, valid_profile):
        valid_profile["image"]["roles"] = "not-a-list"
        with pytest.raises(ProfileError):
            validate_profile(valid_profile)

    def test_roles_defaults_to_empty(self, minimal_profile):
        validate_profile(minimal_profile)
        assert minimal_profile["image"]["roles"] == []


class TestProfileDiscovery:
    def test_discover_existing_profile(self, profile_file, profiles_dir):
        result = discover_profiles(profiles_dir)
        assert "test-profile" in result

    def test_discover_profile_not_found(self, profiles_dir):
        with pytest.raises(ProfileError, match="nonexistent"):
            load_profile("nonexistent", profiles_dir)

    def test_discover_no_profiles_directory(self, tmp_path):
        missing_dir = tmp_path / "no-such-dir"
        with pytest.raises(ProfileError, match="profiles"):
            discover_profiles(missing_dir)

    def test_discover_lists_available_on_not_found(self, profile_file, profiles_dir):
        with pytest.raises(ProfileError, match="test-profile"):
            load_profile("nonexistent", profiles_dir)


class TestPathExpansion:
    def test_tilde_expansion(self, profiles_dir):
        import os

        from tests.conftest import _write_profile_dir

        profile_data = {
            "name": "tilde-test",
            "image": {
                "os": "fedora",
            },
            "agent": {
                "command": "echo run",
            },
            "project": {"workdir": "~/my-project"},
        }
        _write_profile_dir(profiles_dir, "tilde-test", profile_data)
        profile = load_profile("tilde-test", profiles_dir)
        assert profile["project"]["workdir"] == os.path.expanduser("~/my-project")

    def test_env_var_expansion(self, profiles_dir, monkeypatch):
        from tests.conftest import _write_profile_dir

        monkeypatch.setenv("TEST_SANDBOX_DIR", "/opt/sandbox")
        profile_data = {
            "name": "envvar-test",
            "image": {
                "os": "fedora",
            },
            "agent": {
                "command": "echo run",
            },
            "project": {"workdir": "$TEST_SANDBOX_DIR/project"},
        }
        _write_profile_dir(profiles_dir, "envvar-test", profile_data)
        profile = load_profile("envvar-test", profiles_dir)
        assert profile["project"]["workdir"] == "/opt/sandbox/project"


class TestDefaults:
    def test_omitted_runtime_gets_defaults(self, profiles_dir):
        from tests.conftest import _write_profile_dir

        profile_data = {
            "name": "with-runtime",
            "image": {
                "os": "fedora",
            },
            "agent": {
                "command": "echo run",
            },
            "project": {"workdir": "/tmp/project"},
        }
        _write_profile_dir(profiles_dir, "with-runtime", profile_data)
        profile = load_profile("with-runtime", profiles_dir)
        assert profile["runtime"]["access_host_libvirt"] is False
        assert profile["runtime"]["memory"] == "4G"
        assert profile["runtime"]["cpus"] == 4

    def test_disk_defaults_to_20g(self, profiles_dir):
        from tests.conftest import _write_profile_dir

        profile_data = {
            "name": "disk-default",
            "image": {
                "os": "fedora",
            },
            "agent": {
                "command": "echo run",
            },
            "project": {"workdir": "/tmp/project"},
        }
        _write_profile_dir(profiles_dir, "disk-default", profile_data)
        profile = load_profile("disk-default", profiles_dir)
        assert profile["runtime"]["disk"] == "20G"

    def test_omitted_optional_agent_fields_get_defaults(self, profiles_dir):
        from tests.conftest import _write_profile_dir

        profile_data = {
            "name": "minimal-agent",
            "image": {
                "os": "fedora",
            },
            "agent": {
                "command": "echo run",
            },
            "project": {"workdir": "/tmp/project"},
        }
        _write_profile_dir(profiles_dir, "minimal-agent", profile_data)
        profile = load_profile("minimal-agent", profiles_dir)
        assert profile["agent"]["env"] == {}

    def test_omitted_extra_syncs_defaults_to_empty(self, profiles_dir):
        from tests.conftest import _write_profile_dir

        profile_data = {
            "name": "no-syncs",
            "image": {
                "os": "fedora",
            },
            "agent": {
                "command": "echo run",
            },
            "project": {"workdir": "/tmp/project"},
        }
        _write_profile_dir(profiles_dir, "no-syncs", profile_data)
        profile = load_profile("no-syncs", profiles_dir)
        assert profile["project"]["extra_syncs"] == []

    def test_profile_dir_is_set(self, profiles_dir):
        from tests.conftest import _write_profile_dir

        profile_data = {
            "name": "dir-test",
            "image": {
                "os": "fedora",
            },
            "agent": {
                "command": "echo run",
            },
            "project": {"workdir": "/tmp/project"},
        }
        _write_profile_dir(profiles_dir, "dir-test", profile_data)
        profile = load_profile("dir-test", profiles_dir)
        assert profile["_profile_dir"] == str(profiles_dir / "dir-test")

    def test_subdirectory_without_profile_yaml_ignored(self, profiles_dir):
        (profiles_dir / "not-a-profile").mkdir()
        (profiles_dir / "not-a-profile" / "random.txt").write_text("hello")
        result = discover_profiles(profiles_dir)
        assert "not-a-profile" not in result

    def test_omitted_roles_defaults_to_empty(self, profiles_dir):
        from tests.conftest import _write_profile_dir

        profile_data = {
            "name": "no-roles",
            "image": {
                "os": "fedora",
            },
            "agent": {
                "command": "echo run",
            },
            "project": {"workdir": "/tmp/project"},
        }
        _write_profile_dir(profiles_dir, "no-roles", profile_data)
        profile = load_profile("no-roles", profiles_dir)
        assert profile["image"]["roles"] == []


class TestOsRoleVars:
    def test_load_os_role_vars_fedora(self):
        from isolagent.profile import load_os_role_vars

        data = load_os_role_vars("fedora")
        assert "base_image_url" in data
        assert data["base_image_url"].startswith("https://")

    def test_load_os_role_vars_missing_os(self, tmp_path):
        from isolagent.profile import load_os_role_vars

        with pytest.raises(ProfileError, match="not found"):
            load_os_role_vars("nonexistent", roles_dir=tmp_path)

    def test_load_os_role_vars_missing_url(self, tmp_path):
        from isolagent.profile import load_os_role_vars

        os_dir = tmp_path / "bad-os" / "vars"
        os_dir.mkdir(parents=True)
        (os_dir / "main.yaml").write_text("some_other_key: value\n")
        with pytest.raises(ProfileError, match="base_image_url"):
            load_os_role_vars("bad-os", roles_dir=tmp_path)
