import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import urlretrieve

import yaml

from isolagent.libvirt_helpers import (
    check_default_network,
    cleanup_stale_domain,
    create_domain,
    delete_volume,
    destroy_domain,
    discover_guest_ip,
    generate_domain_name,
    generate_domain_xml,
    get_default_pool,
    get_libvirt_connection,
    get_volume_path,
    upload_volume,
    volume_exists,
)
from isolagent.session import ISO_TOOLS, SessionError, find_iso_tool, wait_for_ssh

KVM_DEVICE = "/dev/kvm"
ROLES_DIR = Path(__file__).parent.parent / "roles"


def check_preflight(profile=None):
    try:
        conn = get_libvirt_connection(profile)
        check_default_network(conn)
        get_default_pool(conn)
        conn.close()
    except SessionError as e:
        print(f"Error: libvirt check failed: {e}", file=sys.stderr)
        sys.exit(1)

    if not shutil.which("ansible-playbook"):
        print(
            "Error: 'ansible-playbook' not found in PATH. "
            "Install: dnf install ansible-core (Fedora) / pacman -S ansible (Arch)",
            file=sys.stderr,
        )
        sys.exit(1)

    if not find_iso_tool():
        print(
            f"Error: No ISO creation tool found. Install one of: {', '.join(ISO_TOOLS)}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not Path(KVM_DEVICE).exists():
        print(
            "Error: /dev/kvm not found. KVM is required for image building.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not shutil.which("sshpass"):
        print(
            "Error: 'sshpass' not found in PATH. "
            "Install: dnf install sshpass (Fedora) / pacman -S sshpass (Arch)",
            file=sys.stderr,
        )
        sys.exit(1)


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class DownloadError(Exception):
    pass


def download_base_image(url, sha256=None, downloads_dir=None):
    if downloads_dir:
        dest = Path(downloads_dir)
    else:
        xdg_cache = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
        dest = Path(xdg_cache) / "isolagent"

    filename = url.rsplit("/", 1)[-1]
    cached_path = dest / filename
    if cached_path.exists():
        if sha256:
            actual = _sha256_file(cached_path)
            if actual != sha256:
                print(f"SHA-256 mismatch for cached {cached_path}, re-downloading...")
                cached_path.unlink()
            else:
                return cached_path
        else:
            return cached_path
    dest.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url}...")
    urlretrieve(url, str(cached_path))
    if sha256:
        actual = _sha256_file(cached_path)
        if actual != sha256:
            cached_path.unlink()
            raise DownloadError(
                f"SHA-256 mismatch: expected {sha256}, got {actual}"
            )
    return cached_path


def image_exists(profile_name, images_base=None):
    try:
        conn = get_libvirt_connection()
        vol_name = f"isolagent-{profile_name}"
        exists = volume_exists(conn, vol_name)
        conn.close()
        return exists
    except SessionError:
        return False


BUILD_SSH_PASSWORD = "isolagent-build"


def _build_cloud_init_userdata():
    return (
        "#cloud-config\n"
        "disable_root: false\n"
        "ssh_pwauth: true\n"
        "chpasswd:\n"
        f"  list: root:{BUILD_SSH_PASSWORD}\n"
        "  expire: false\n"
        "runcmd:\n"
        "  - sed -i 's/^#\\?PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config\n"
        "  - rm -f /etc/ssh/sshd_config.d/*cloud-init* /etc/ssh/sshd_config.d/*50-redhat*\n"
        "  - echo 'PasswordAuthentication yes' > /etc/ssh/sshd_config.d/00-isolagent-build.conf\n"
        "  - systemctl restart sshd\n"
    )


def _build_cloud_init_metadata():
    return "instance-id: isolagent-build\nlocal-hostname: isolagent\n"


def assemble_roles(profile):
    os_name = profile["image"]["os"]
    roles = ["base", os_name]
    if profile.get("runtime", {}).get("access_host_libvirt", False):
        roles.append("libvirt-bridge")
    roles.extend(profile["image"].get("roles", []))
    return roles


def generate_playbook(roles):
    playbook = [
        {
            "hosts": "all",
            "become": True,
            "roles": list(roles),
        }
    ]
    return yaml.dump(playbook, default_flow_style=False)


def _build_roles_path(profile, roles_dir=None):
    roles_dir = Path(roles_dir) if roles_dir else ROLES_DIR
    paths = []
    profile_dir = profile.get("_profile_dir")
    if profile_dir:
        profile_roles = Path(profile_dir) / "roles"
        if profile_roles.is_dir():
            paths.append(str(profile_roles))
    paths.append(str(roles_dir))
    return ":".join(paths)


def run_build(profile, force=False):
    from isolagent.profile import load_os_role_vars

    check_preflight(profile)

    name = profile["name"]
    vol_name = f"isolagent-{name}"

    rebuild = image_exists(name)
    if not force and rebuild:
        answer = input(f"Image for '{name}' already exists. Rebuild? [y/N] ")
        if answer.lower() != "y":
            print("Aborted.")
            return

    conn = None
    domain = None
    domain_name = None

    try:
        conn = get_libvirt_connection(profile)

        os_vars = load_os_role_vars(profile["image"]["os"])
        cached_image = download_base_image(
            os_vars["base_image_url"],
            sha256=os_vars.get("base_image_sha256"),
        )

        print(f"Uploading base image to libvirt storage pool as '{vol_name}'...")
        capacity_bytes = cached_image.stat().st_size
        upload_volume(conn, vol_name, str(cached_image), capacity_bytes)

        roles = assemble_roles(profile)
        playbook_content = generate_playbook(roles)
        roles_path = _build_roles_path(profile)

        extra_vars = {
            "profile_name": name,
            "project_root": str(Path(__file__).resolve().parent.parent),
        }

        with tempfile.TemporaryDirectory(prefix="isolagent-build-") as tmpdir:
            os.chmod(tmpdir, 0o755)
            tmpdir_path = Path(tmpdir)

            playbook_path = tmpdir_path / "playbook.yaml"
            playbook_path.write_text(playbook_content)

            userdata_path = tmpdir_path / "user-data"
            userdata_path.write_text(_build_cloud_init_userdata())

            metadata_path = tmpdir_path / "meta-data"
            metadata_path.write_text(_build_cloud_init_metadata())

            iso_path = tmpdir_path / "cidata.iso"
            iso_tool = find_iso_tool()
            iso_cmd = [
                iso_tool,
                "-output", str(iso_path),
                "-volid", "cidata",
                "-joliet",
                "-rock",
                str(userdata_path),
                str(metadata_path),
            ]
            result = subprocess.run(iso_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(
                    f"Error: Failed to create cloud-init ISO: {result.stderr}",
                    file=sys.stderr,
                )
                sys.exit(1)

            domain_name = generate_domain_name(name)
            console_log_path = tmpdir_path / "console.log"

            runtime = profile.get("runtime", {})
            memory = runtime.get("memory", "4G")
            cpus = runtime.get("cpus", 4)

            disk_path = get_volume_path(conn, vol_name)

            domain_xml = generate_domain_xml(
                name=domain_name,
                memory=memory,
                cpus=cpus,
                disk_path=disk_path,
                cloud_init_iso_path=str(iso_path),
                console_log_path=str(console_log_path),
                profile_name=name,
            )

            cleanup_stale_domain(conn, domain_name)

            print(f"Starting build VM '{domain_name}'...")
            domain = create_domain(conn, domain_xml)

            print("Discovering guest IP...")
            guest_ip = discover_guest_ip(domain, conn)
            print(f"Guest IP: {guest_ip}")

            print("Waiting for SSH to become available...")
            build_ssh_base = [
                "sshpass", "-p", BUILD_SSH_PASSWORD,
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "LogLevel=ERROR",
                f"root@{guest_ip}",
            ]
            wait_for_ssh(build_ssh_base, timeout=120, interval=2)

            print("Running Ansible playbook...")
            cmd = [
                "ansible-playbook", str(playbook_path),
                "-i", f"{guest_ip},",
                "--extra-vars", json.dumps(extra_vars),
                "-e", "ansible_user=root",
                "-e", f"ansible_ssh_pass={BUILD_SSH_PASSWORD}",
                "-e", f"roles_path={roles_path}",
            ]
            env = os.environ.copy()
            env["ANSIBLE_ROLES_PATH"] = roles_path
            env["ANSIBLE_HOST_KEY_CHECKING"] = "False"

            result = subprocess.run(cmd, env=env)
            if result.returncode != 0:
                raise RuntimeError(
                    f"Ansible playbook failed with exit code {result.returncode}"
                )

            print("Shutting down build VM...")
            subprocess.run(
                [
                    "sshpass", "-p", BUILD_SSH_PASSWORD,
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "LogLevel=ERROR",
                    f"root@{guest_ip}",
                    "sync",
                ],
                capture_output=True,
                timeout=30,
            )
            destroy_domain(domain)
            domain = None

        print(f"Image built successfully: {vol_name}")

    except Exception as e:
        print(f"Error during build: {e}", file=sys.stderr)
        if domain:
            destroy_domain(domain)
        if conn and vol_name:
            delete_volume(conn, vol_name)
        if conn:
            conn.close()
        sys.exit(1)

    if conn:
        conn.close()
