import argparse
import sys
from pathlib import Path

from isolagent.builder import run_build
from isolagent.profile import ProfileError, load_profile
from isolagent.session import SessionError, SessionRunner


def _default_profiles_dir():
    return Path(__file__).parent.parent / "profiles"


def _apply_overrides(profile, args):
    if getattr(args, "memory", None):
        profile["runtime"]["memory"] = args.memory
    if getattr(args, "cpus", None):
        profile["runtime"]["cpus"] = args.cpus
    if getattr(args, "disk", None):
        profile["runtime"]["disk"] = args.disk


def cmd_run(args):
    import signal

    profiles_dir = Path(args.profiles_dir) if args.profiles_dir else _default_profiles_dir()
    try:
        profile = load_profile(args.profile, profiles_dir)
    except ProfileError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    shell = getattr(args, "shell", False)
    output_mode = getattr(args, "output_mode", None)
    if not shell and not output_mode:
        print(
            "error: --output-mode is required unless --shell is used",
            file=sys.stderr,
        )
        sys.exit(1)
    if output_mode == "sync" and not getattr(args, "output_dir", None):
        print(
            "error: --output-dir is required when using --output-mode sync",
            file=sys.stderr,
        )
        sys.exit(1)
    _apply_overrides(profile, args)

    try:
        runner = SessionRunner(
            profile,
            output_mode=output_mode,
            output_dir=getattr(args, "output_dir", None),
            overwrite=getattr(args, "overwrite", False),
            shell=shell,
        )
    except SessionError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    def sigterm_handler(_signum, _frame):
        raise SystemExit(1)

    signal.signal(signal.SIGTERM, sigterm_handler)

    try:
        runner.preflight()
    except SessionError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    try:
        runner.init()
        runner.setup()
        runner.run()
    finally:
        runner.teardown()


def cmd_build(args):
    profiles_dir = Path(args.profiles_dir) if args.profiles_dir else _default_profiles_dir()
    try:
        profile = load_profile(args.profile, profiles_dir)
    except ProfileError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    force = getattr(args, "force", False)
    run_build(profile, force=force)


def cmd_list(args):
    import xml.etree.ElementTree as ET

    from isolagent.libvirt_helpers import get_libvirt_connection

    try:
        conn = get_libvirt_connection()
    except SessionError as e:
        print(f"Cannot connect to libvirt: {e}", file=sys.stderr)
        sys.exit(1)

    domains = conn.listAllDomains(0)
    isolagent_domains = [d for d in domains if d.name().startswith("isolagent-")]

    if not isolagent_domains:
        print("No active sessions")
        conn.close()
        return

    headers = ("Domain", "Profile", "Guest IP", "State")
    rows = []
    for domain in isolagent_domains:
        name = domain.name()

        profile_name = ""
        try:
            xml_str = domain.XMLDesc(0)
            root = ET.fromstring(xml_str)
            ns = {"isolagent": "http://isolagent.local/"}
            elem = root.find(".//isolagent:profile", ns)
            if elem is not None and elem.text:
                profile_name = elem.text
        except Exception:
            pass

        guest_ip = "pending"
        try:
            import libvirt

            ifaces = domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE)
            for _iface, data in ifaces.items():
                for addr in data.get("addrs", []):
                    if addr["type"] == libvirt.VIR_IP_ADDR_TYPE_IPV4 and not addr[
                        "addr"
                    ].startswith("127."):
                        guest_ip = addr["addr"]
                        break
                if guest_ip != "pending":
                    break
        except Exception:
            pass

        state_names = {
            0: "nostate",
            1: "running",
            2: "blocked",
            3: "paused",
            4: "shutdown",
            5: "shutoff",
            6: "crashed",
            7: "suspended",
        }
        try:
            state_num, _ = domain.state()
            state = state_names.get(state_num, f"unknown({state_num})")
        except Exception:
            state = "unknown"

        rows.append((name, profile_name, guest_ip, state))

    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print(fmt.format(*("-" * w for w in widths)))
    for row in rows:
        print(fmt.format(*row))

    conn.close()


def build_parser():
    parser = argparse.ArgumentParser(
        prog="isolagent",
        description="Run fully autonomous LLM agents in an isolated VM",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Launch a session")
    run_parser.add_argument("profile", help="Profile name")
    run_parser.add_argument("--profiles-dir", help="Path to profiles directory")
    run_parser.add_argument("--memory", help="Override guest memory (e.g. 8G)")
    run_parser.add_argument("--cpus", type=int, help="Override guest vCPUs")
    run_parser.add_argument(
        "--disk",
        help="Override guest disk size (e.g. 40G). Format: positive integer with unit M/G/T",
    )
    run_parser.add_argument(
        "--output-mode",
        choices=["patch", "sync", "none"],
        help="Output extraction mode: patch/sync/none. Required unless --shell.",
    )
    run_parser.add_argument(
        "--shell",
        action="store_true",
        help="Drop into an interactive SSH shell instead of running the agent",
    )
    run_parser.add_argument(
        "--output-dir",
        help="Output directory for patch/sync (required for sync mode)",
    )
    run_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow sync into a non-empty output directory",
    )
    run_parser.set_defaults(func=cmd_run)

    build_parser = subparsers.add_parser("build", help="Build an image")
    build_parser.add_argument("profile", help="Profile name")
    build_parser.add_argument("--profiles-dir", help="Path to profiles directory")
    build_parser.add_argument("--force", action="store_true", help="Rebuild without confirmation")
    build_parser.set_defaults(func=cmd_build)

    list_parser = subparsers.add_parser("list", help="List active sessions")
    list_parser.set_defaults(func=cmd_list)

    return parser


def main():
    # Suppress libvirt's C-level default error handler which prints to stderr
    # before Python can catch the exception; Python libvirtError carries the
    # same message, so no diagnostic information is lost.
    import libvirt

    libvirt.registerErrorHandler(lambda _ctx, _err: None, None)

    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
