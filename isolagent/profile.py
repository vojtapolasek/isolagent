import json
import os
from pathlib import Path

import jsonschema
import yaml

_SCHEMA_PATH = Path(__file__).parent / "profile_schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text())

_RUNTIME_DEFAULTS = {
    "access_host_libvirt": False,
    "memory": "4G",
    "cpus": 4,
}

_AGENT_DEFAULTS = {
    "env": {},
}

_IMAGE_DEFAULTS = {
    "roles": [],
}

_PROJECT_DEFAULTS = {
    "extra_syncs": [],
}

_PATH_FIELDS = {
    ("project", "workdir"),
    ("project", "extra_syncs"),
}


class ProfileError(Exception):
    pass


def _expand_path(value):
    if isinstance(value, str):
        return os.path.expandvars(os.path.expanduser(value))
    return value


def _expand_paths(profile):
    for section_key, field_key in _PATH_FIELDS:
        section = profile.get(section_key, {})
        if field_key not in section or section[field_key] is None:
            continue
        value = section[field_key]
        if isinstance(value, list):
            section[field_key] = [_expand_path(v) for v in value]
        elif isinstance(value, dict):
            section[field_key] = {k: _expand_path(v) for k, v in value.items()}
        else:
            section[field_key] = _expand_path(value)


def _apply_defaults(profile):
    if "runtime" not in profile:
        profile["runtime"] = {}
    for key, default in _RUNTIME_DEFAULTS.items():
        profile["runtime"].setdefault(key, default if not isinstance(default, list) else [])

    if "image" in profile:
        for key, default in _IMAGE_DEFAULTS.items():
            if isinstance(default, list):
                profile["image"].setdefault(key, [])
            else:
                profile["image"].setdefault(key, default)

    if "agent" in profile:
        for key, default in _AGENT_DEFAULTS.items():
            if isinstance(default, dict):
                profile["agent"].setdefault(key, {})
            elif isinstance(default, list):
                profile["agent"].setdefault(key, [])
            else:
                profile["agent"].setdefault(key, default)

    if "project" in profile:
        for key, default in _PROJECT_DEFAULTS.items():
            if isinstance(default, list):
                profile["project"].setdefault(key, [])
            else:
                profile["project"].setdefault(key, default)


def validate_profile(profile):
    _apply_defaults(profile)
    try:
        jsonschema.validate(instance=profile, schema=_SCHEMA)
    except jsonschema.ValidationError as e:
        if e.absolute_path:
            field = ".".join(str(p) for p in e.absolute_path)
        elif e.absolute_schema_path:
            field = ".".join(str(p) for p in e.absolute_schema_path)
        else:
            field = "(root)"
        raise ProfileError(f"Profile validation error at '{field}': {e.message}") from e


def discover_profiles(profiles_dir):
    profiles_dir = Path(profiles_dir)
    if not profiles_dir.is_dir():
        raise ProfileError(f"Profiles directory not found: {profiles_dir}")
    profiles = {}
    for path in sorted(profiles_dir.iterdir()):
        if path.is_dir() and (path / "profile.yaml").is_file():
            profiles[path.name] = path / "profile.yaml"
    return profiles


def load_profile(name, profiles_dir):
    available = discover_profiles(profiles_dir)
    if name not in available:
        available_names = ", ".join(sorted(available.keys())) or "(none)"
        raise ProfileError(
            f"Profile '{name}' not found (nonexistent). Available profiles: {available_names}"
        )
    path = available[name]
    with open(path) as f:
        profile = yaml.safe_load(f)
    _apply_defaults(profile)
    _expand_paths(profile)
    validate_profile(profile)
    profile["_profile_dir"] = str(path.parent.resolve())
    return profile


_ROLES_DIR = Path(__file__).parent.parent / "roles"


def load_os_role_vars(os_name, roles_dir=None):
    roles_dir = Path(roles_dir) if roles_dir else _ROLES_DIR
    vars_file = roles_dir / os_name / "vars" / "main.yaml"
    if not vars_file.exists():
        raise ProfileError(f"OS role '{os_name}' not found: {vars_file} does not exist")
    with open(vars_file) as f:
        data = yaml.safe_load(f)
    if not data or "base_image_url" not in data:
        raise ProfileError(f"OS role '{os_name}' vars missing required field 'base_image_url'")
    return data
