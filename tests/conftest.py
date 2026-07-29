import copy
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).parent.parent

VALID_PROFILE = {
    "name": "test-profile",
    "image": {
        "os": "fedora",
        "roles": ["agent-test"],
    },
    "agent": {
        "command": "myagent --run",
    },
    "runtime": {
        "access_host_libvirt": False,
        "memory": "4G",
        "cpus": 4,
    },
    "project": {
        "workdir": "/tmp/test-project",
    },
}


MINIMAL_PROFILE = {
    "name": "minimal",
    "image": {
        "os": "fedora",
    },
    "agent": {
        "command": "myagent --run",
    },
    "project": {
        "workdir": "/tmp/test-project",
    },
}


def _write_profile_dir(profiles_dir, name, data):
    """Write a profile as a directory with profile.yaml inside."""
    profile_dir = profiles_dir / name
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / "profile.yaml").write_text(yaml.dump(data))
    return profile_dir


@pytest.fixture
def valid_profile():
    return copy.deepcopy(VALID_PROFILE)


@pytest.fixture
def minimal_profile():
    return copy.deepcopy(MINIMAL_PROFILE)


@pytest.fixture
def profiles_dir(tmp_path):
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    return profiles


@pytest.fixture
def profile_file(profiles_dir):
    profile_dir = profiles_dir / "test-profile"
    profile_dir.mkdir()
    path = profile_dir / "profile.yaml"
    path.write_text(yaml.dump(VALID_PROFILE))
    return path


@pytest.fixture(scope="session")
def integration_prerequisites():
    import os

    from isolagent.builder import download_base_image
    from isolagent.profile import load_os_role_vars

    os_vars = load_os_role_vars("fedora")

    xdg_cache = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
    downloads_dir = Path(xdg_cache) / "isolagent"
    existing = list(downloads_dir.glob("Fedora-Cloud*.qcow2")) if downloads_dir.exists() else []
    we_downloaded = not bool(existing)

    cloud_image = download_base_image(
        os_vars["base_image_url"],
        sha256=os_vars.get("base_image_sha256"),
        downloads_dir=downloads_dir,
    )

    yield cloud_image

    if we_downloaded and cloud_image.exists():
        cloud_image.unlink()
