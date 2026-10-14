import contextlib
import fcntl
import os
import shlex
import shutil
import signal
import subprocess
import time
from pathlib import Path

ISO_TOOLS = ["xorrisofs", "genisoimage", "mkisofs"]


def find_iso_tool():
    for tool in ISO_TOOLS:
        if shutil.which(tool):
            return tool
    return None


def wait_for_ssh(ssh_cmd_base, timeout=60, interval=1):
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            ssh_cmd_base + ["-o", "ConnectTimeout=1", "true"],
            capture_output=True,
        )
        if result.returncode == 0:
            return
        time.sleep(interval)
    raise SessionError(f"SSH did not become available within {timeout} seconds")


class SessionError(Exception):
    pass


class SessionRunner:
    def __init__(self, profile, output_mode=None, output_dir=None, overwrite=False, shell=False):
        self.profile = profile
        self.output_mode = output_mode
        self.output_dir = output_dir
        self.overwrite = overwrite
        self.shell = shell

        self.project_root = Path(__file__).parent.parent
        self.conn = None
        self.domain = None
        self.domain_name = None
        self.overlay_vol_name = None
        self.guest_ip = None
        self.cidata_dir = None
        self.cidata_iso = None
        self.console_log = None
        self.initial_head = None
        self.iso_tool = None
        self.socat_lock_fd = None

    def preflight(self):
        from isolagent.libvirt_helpers import (
            check_default_network,
            get_default_pool,
            get_libvirt_connection,
            volume_exists,
        )

        name = self.profile["name"]

        self.conn = get_libvirt_connection(self.profile)
        check_default_network(self.conn)
        get_default_pool(self.conn)

        if not volume_exists(self.conn, f"isolagent-{name}"):
            raise SessionError(
                f"Base image volume 'isolagent-{name}' not found"
                f" — run 'isolagent build {name}' first"
            )

        self.iso_tool = find_iso_tool()
        if not self.iso_tool:
            raise SessionError(
                f"No ISO creation tool found — install one of: {', '.join(ISO_TOOLS)}"
            )

        self._validate_extra_syncs()

        if self.output_dir:
            self._check_output_dir()

        if self.output_mode == "patch":
            self._check_patch_mode_git()

    def _check_output_dir(self):
        if not os.path.isdir(self.output_dir):
            raise SessionError(
                f"{self.output_dir} does not exist — create it with: mkdir -p {self.output_dir}"
            )
        if not os.access(self.output_dir, os.W_OK):
            raise SessionError(f"{self.output_dir} is not writable")
        if (
            self.output_mode == "sync"
            and not self.overwrite
            and any(Path(self.output_dir).iterdir())
        ):
            raise SessionError(
                f"{self.output_dir} is not empty"
                " — use --overwrite to sync into a non-empty directory"
            )

    def _check_patch_mode_git(self):
        workdir = self.profile["project"]["workdir"]
        if not os.path.isdir(workdir):
            raise SessionError(
                f"{workdir} does not exist — --output-mode patch requires a valid workdir"
            )
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            cwd=workdir,
        )
        if result.returncode != 0:
            raise SessionError(
                f"{workdir} is not a git repository — --output-mode patch requires a git repo"
            )
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=workdir,
        )
        if result.returncode != 0:
            raise SessionError(
                f"{workdir} has no commits"
                " — make an initial commit before using --output-mode patch"
            )

    def _validate_extra_syncs(self):
        extra_syncs = self.profile.get("project", {}).get("extra_syncs", [])
        basenames = ["project"]
        for path in extra_syncs:
            basename = Path(path).name
            if basename in basenames:
                raise SessionError(
                    f"Extra sync basename collision: '{basename}'"
                    " conflicts with an existing sync target"
                )
            basenames.append(basename)

    def _ssh_cmd_base(self):
        return [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "LogLevel=ERROR",
            f"root@{self.guest_ip}",
        ]

    def _ssh_run(self, cmd):
        full_cmd = self._ssh_cmd_base() + [cmd]
        return subprocess.run(full_cmd, capture_output=True, text=True)

    def _ssh_exec(self, cmd):
        result = self._ssh_run(cmd)
        if result.returncode != 0:
            raise SessionError(f"SSH command failed: {cmd}\n{result.stderr}")
        return result.stdout.strip()

    def _rsync_cmd(self, src, dest):
        ssh_cmd = " ".join(
            [
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                "-o",
                "IdentitiesOnly=yes",
                "-o",
                "LogLevel=ERROR",
            ]
        )
        return [
            "rsync",
            "-az",
            "--delete",
            "--chown=root:root",
            "-e",
            ssh_cmd,
            src,
            dest,
        ]

    def _rsync(self, src, dest):
        cmd = self._rsync_cmd(src, dest)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise SessionError(f"rsync failed: {result.stderr}")

    def _cloud_init_network_config(self):
        return (
            "network:\n"
            "  version: 2\n"
            "  ethernets:\n"
            "    all-en:\n"
            "      match:\n"
            '        name: "en*"\n'
            "      dhcp4: true\n"
        )

    def _cloud_init_meta_data(self):
        return f"instance-id: isolagent-{self.domain_name}\nlocal-hostname: isolagent\n"

    def _cloud_init_user_data(self):
        return (
            "#cloud-config\ndisable_root: false\n"
            'growpart:\n  mode: auto\n  devices: ["/"]\n'
            "resize_rootfs: true\n"
            "users:\n  - name: root\n    lock_passwd: false\n"
        )

    def _iso_cmd(self, cidata_dir, iso_path):
        return [
            self.iso_tool,
            "-output",
            iso_path,
            "-volid",
            "cidata",
            "-joliet",
            "-rock",
            cidata_dir + "/",
        ]

    def _sync_in_commands(self):
        cmds = []
        workdir = self.profile["project"]["workdir"]
        if not workdir.endswith("/"):
            workdir += "/"
        guest_dest = f"root@{self.guest_ip}:/isolagent/project/"
        cmds.append(self._rsync_cmd(workdir, guest_dest))

        for path in self.profile.get("project", {}).get("extra_syncs", []):
            basename = Path(path).name
            src = path if path.endswith("/") else path + "/"
            dest = f"root@{self.guest_ip}:/isolagent/{basename}/"
            cmds.append(self._rsync_cmd(src, dest))
        return cmds

    def _guest_file_commands(self):
        profile_dir = Path(self.profile.get("_profile_dir", ""))
        guest_files_dir = profile_dir / "guest-files"
        if not guest_files_dir.is_dir():
            return []
        commands = []
        for host_path in sorted(guest_files_dir.rglob("*")):
            if not host_path.is_file():
                continue
            rel = host_path.relative_to(guest_files_dir)
            guest_path = f"/{rel}"
            commands.append(
                {
                    "guest_path": guest_path,
                    "host_path": str(host_path),
                }
            )
        return commands

    def _env_prefix(self):
        env = self.profile.get("agent", {}).get("env", {})
        if not env:
            return ""
        env_pairs = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())
        return f"env {env_pairs} "

    def _agent_tmux_cmd(self):
        command = self.profile["agent"]["command"]
        return f"cd /isolagent/project && {self._env_prefix()}{command}"

    def _shell_cmd(self):
        return f"cd /isolagent/project && {self._env_prefix()}bash"

    def _socat_cmd(self):
        return [
            "socat",
            "VSOCK-LISTEN:16509,reuseaddr,fork",
            "UNIX-CONNECT:/var/run/libvirt/libvirt-sock",
        ]

    def _socat_dir(self):
        return Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "isolagent"

    def _start_socat_with_flock(self, timeout=10):
        socat_dir = self._socat_dir()
        socat_dir.mkdir(parents=True, exist_ok=True)
        pid_path = socat_dir / "socat.pid"

        fd = os.open(str(pid_path), os.O_RDWR | os.O_CREAT)
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    os.close(fd)
                    raise SessionError(
                        f"Could not acquire socat lock {pid_path}: "
                        f"lock acquisition timed out after {timeout}s"
                    ) from exc
                time.sleep(0.2)

        alive = False
        try:
            content = os.pread(fd, 64, 0).decode().strip()
            if content:
                pid = int(content)
                os.kill(pid, 0)
                alive = True
        except (ValueError, OSError):
            pass

        if not alive:
            proc = subprocess.Popen(
                self._socat_cmd(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            os.ftruncate(fd, 0)
            os.pwrite(fd, str(proc.pid).encode(), 0)

        fcntl.flock(fd, fcntl.LOCK_SH)
        self.socat_lock_fd = fd

    def _stop_socat_with_flock(self):
        if self.socat_lock_fd is not None:
            with contextlib.suppress(Exception):
                os.close(self.socat_lock_fd)
            self.socat_lock_fd = None

        pid_path = self._socat_dir() / "socat.pid"

        try:
            fd = os.open(str(pid_path), os.O_RDWR)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                content = os.pread(fd, 64, 0).decode().strip()
                if content:
                    pid = int(content)
                    with contextlib.suppress(OSError):
                        os.kill(pid, signal.SIGTERM)
                with contextlib.suppress(OSError):
                    pid_path.unlink()
            except OSError:
                pass
            finally:
                os.close(fd)
        except OSError:
            pass

    def init(self):
        from isolagent.libvirt_helpers import (
            create_overlay_volume,
            generate_domain_name,
            get_volume_virtual_size,
            parse_size_bytes,
        )

        self.domain_name = generate_domain_name(self.profile["name"])

        base_vol_name = f"isolagent-{self.profile['name']}"
        disk_str = self.profile.get("runtime", {}).get("disk", "20G")
        try:
            capacity_bytes = parse_size_bytes(disk_str)
        except ValueError as e:
            raise SessionError(
                f"Invalid disk size '{disk_str}': {e}. "
                "Expected a positive integer with unit M, G, or T (e.g. '20G')"
            ) from e

        base_size_bytes = get_volume_virtual_size(self.conn, base_vol_name)
        if capacity_bytes < base_size_bytes:
            min_str = (
                f"{base_size_bytes // 1024**3}G"
                if base_size_bytes % 1024**3 == 0
                else f"{base_size_bytes} bytes"
            )
            raise SessionError(
                f"Configured disk size '{disk_str}' is smaller than the base "
                f"image virtual size — set disk to at least {min_str}"
            )

        self.overlay_vol_name = f"{self.domain_name}-overlay"
        create_overlay_volume(
            self.conn,
            self.overlay_vol_name,
            base_vol_name,
            capacity_bytes,
        )

        self.cidata_dir = Path(f"/tmp/isolagent-{self.domain_name}-cidata")
        self.cidata_iso = Path(f"/tmp/isolagent-{self.domain_name}-cidata.iso")
        if self.cidata_dir.exists():
            shutil.rmtree(self.cidata_dir)
        self.cidata_dir.mkdir(parents=True)
        (self.cidata_dir / "meta-data").write_text(self._cloud_init_meta_data())
        (self.cidata_dir / "user-data").write_text(self._cloud_init_user_data())
        (self.cidata_dir / "network-config").write_text(self._cloud_init_network_config())
        subprocess.run(
            self._iso_cmd(str(self.cidata_dir), str(self.cidata_iso)),
            check=True,
            capture_output=True,
        )

        access_host_libvirt = self.profile.get("runtime", {}).get(
            "access_host_libvirt",
            False,
        )
        if access_host_libvirt:
            self._start_socat_with_flock()

        self.console_log = Path(f"/tmp/isolagent-{self.domain_name}-console.log")

    def setup(self):

        from isolagent.libvirt_helpers import (
            cleanup_stale_domain,
            create_domain,
            discover_guest_ip,
            generate_domain_xml,
            get_volume_path,
        )

        runtime = self.profile.get("runtime", {})
        memory = runtime.get("memory", "4G")
        cpus = runtime.get("cpus", 4)
        disk_path = get_volume_path(self.conn, self.overlay_vol_name)

        domain_xml = generate_domain_xml(
            name=self.domain_name,
            memory=memory,
            cpus=cpus,
            disk_path=disk_path,
            cloud_init_iso_path=str(self.cidata_iso),
            console_log_path=str(self.console_log),
            profile_name=self.profile["name"],
        )

        cleanup_stale_domain(self.conn, self.domain_name)
        self.domain = create_domain(self.conn, domain_xml)
        self.guest_ip = discover_guest_ip(self.domain, self.conn)

        wait_for_ssh(self._ssh_cmd_base())

        for cmd in self._sync_in_commands():
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise SessionError(f"rsync failed: {result.stderr}")

        for gf in self._guest_file_commands():
            guest_dir = str(Path(gf["guest_path"]).parent)
            self._ssh_exec(f"mkdir -p {guest_dir}")
            scp_cmd = [
                "scp",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                "-o",
                "IdentitiesOnly=yes",
                "-o",
                "LogLevel=ERROR",
                gf["host_path"],
                f"root@{self.guest_ip}:{gf['guest_path']}",
            ]
            result = subprocess.run(
                scp_cmd,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise SessionError(
                    f"File upload failed: {gf['host_path']} -> {gf['guest_path']}: {result.stderr}"
                )

        if self.profile.get("runtime", {}).get("access_host_libvirt", False):
            self._ssh_exec("systemctl start vsock-libvirt-bridge")

        if self.output_mode == "patch":
            self.initial_head = self._ssh_exec("cd /isolagent/project && git rev-parse HEAD")

    def _patch_format_cmd(self):
        return f"cd /isolagent/project && git format-patch {self.initial_head} --stdout"

    def _patch_output_path(self):
        import time as _time

        output_dir = self.output_dir or self.profile["project"]["workdir"]
        timestamp = _time.strftime("%Y-%m-%d-%H%M%S")
        return f"{output_dir}/isolagent-{timestamp}.patch"

    def _sync_out_cmd(self):
        output_dir = self.output_dir or self.profile["project"]["workdir"]
        if not output_dir.endswith("/"):
            output_dir += "/"

        ssh_cmd = " ".join(
            [
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                "-o",
                "IdentitiesOnly=yes",
                "-o",
                "LogLevel=ERROR",
            ]
        )
        cmd = [
            "rsync",
            "-az",
            "--delete",
            "-e",
            ssh_cmd,
            f"root@{self.guest_ip}:/isolagent/project/",
            output_dir,
        ]
        return cmd

    def _extract_output(self):
        if self.shell or not self.output_mode:
            return

        if self.output_mode == "none":
            print("Output mode is 'none' — changes discarded")
            return

        reachable = self._ssh_run("true").returncode == 0
        if not reachable:
            print("Warning: VM unreachable, skipping output extraction")
            return

        if self.output_mode == "patch":
            self._extract_patch()
        elif self.output_mode == "sync":
            self._extract_sync()

    def _extract_patch(self):
        uncommitted = self._ssh_run("cd /isolagent/project && git status --porcelain")
        if uncommitted.stdout.strip():
            print("Warning: Uncommitted changes in guest (not included in patch):")
            print(uncommitted.stdout)

        current_head = self._ssh_run("cd /isolagent/project && git rev-parse HEAD").stdout.strip()

        if current_head == self.initial_head:
            print("No commits made by agent")
            return

        patch_path = self._patch_output_path()
        result = self._ssh_run(self._patch_format_cmd())
        if result.returncode == 0 and result.stdout:
            Path(patch_path).write_text(result.stdout)
            print(f"Patch saved: {patch_path}")
            output_dir = self.output_dir or self.profile["project"]["workdir"]
            print(f"  Apply with: cd {output_dir} && git am {Path(patch_path).name}")

    def _extract_sync(self):
        cmd = self._sync_out_cmd()
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Warning: sync-out failed: {result.stderr}")
        else:
            output_dir = self.output_dir or self.profile["project"]["workdir"]
            print(f"Synced output to: {output_dir}")

    def run(self):
        if self.shell:
            subprocess.run(
                self._ssh_cmd_base() + ["-t", self._shell_cmd()],
            )
            return

        agent_cmd = self._agent_tmux_cmd()
        self._ssh_exec(f"tmux new-session -d -s isolagent '{agent_cmd}'")

        max_failures = 10
        consecutive_failures = 0
        while consecutive_failures < max_failures:
            check = subprocess.run(
                self._ssh_cmd_base()
                + [
                    "-o",
                    "ConnectTimeout=5",
                    "tmux has-session -t isolagent",
                ],
                capture_output=True,
            )
            if check.returncode != 0:
                if check.returncode != 255:
                    break
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    print(f"Warning: Lost connection to VM after {max_failures} attempts")
                    break
                import time

                time.sleep(2)
                continue

            consecutive_failures = 0
            subprocess.run(
                self._ssh_cmd_base() + ["-t", "tmux attach-session -t isolagent"],
            )

    def teardown(self):
        try:
            self._extract_output()
        except Exception as exc:
            import sys as _sys

            print(
                f"Warning: output extraction failed: {exc}",
                file=_sys.stderr,
            )

        if self.domain is not None:
            with contextlib.suppress(Exception):
                from isolagent.libvirt_helpers import destroy_domain

                destroy_domain(self.domain)

        if self.overlay_vol_name is not None and self.conn is not None:
            with contextlib.suppress(Exception):
                from isolagent.libvirt_helpers import delete_volume

                delete_volume(self.conn, self.overlay_vol_name)

        access_host_libvirt = self.profile.get("runtime", {}).get(
            "access_host_libvirt",
            False,
        )
        if access_host_libvirt:
            with contextlib.suppress(Exception):
                self._stop_socat_with_flock()

        if self.cidata_dir and self.cidata_dir.exists():
            with contextlib.suppress(Exception):
                shutil.rmtree(self.cidata_dir)

        if self.cidata_iso and self.cidata_iso.exists():
            with contextlib.suppress(Exception):
                self.cidata_iso.unlink()

        if self.console_log and self.console_log.exists():
            with contextlib.suppress(Exception):
                self.console_log.unlink()

        if self.conn is not None:
            with contextlib.suppress(Exception):
                self.conn.close()
