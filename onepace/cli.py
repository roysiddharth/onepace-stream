"""Unified CLI dispatching to the project's existing scripts.

Usage: python3 -m onepace <command> [args]
"""
import argparse
import subprocess
import sys
from pathlib import Path

from onepace import watch as watch_mod

ROOT = Path(__file__).resolve().parent.parent


def run_script(*parts):
    return subprocess.run(["bash", str(ROOT / Path(*parts))], cwd=ROOT).returncode


def setup_mac(args):
    return subprocess.run(["bash", str(ROOT / "client/setup-mac.sh"), args.samba_user], cwd=ROOT).returncode


def setup_server(args):
    code = run_script("server", "setup-transmission.sh")
    if code != 0:
        return code
    return run_script("server", "setup-samba.sh")


def magnets_add(args):
    return run_script("server", "add-magnets.sh")


def ledger_refresh(args):
    return run_script("server", "build-ledger-remote.sh")


def progress(args):
    binary = ROOT / "server/watchtui/watchtui"
    if binary.exists():
        return subprocess.run([str(binary), str(args.interval)], cwd=ROOT).returncode
    return subprocess.run(
        ["bash", str(ROOT / "server/watch-progress.sh"), str(args.interval)], cwd=ROOT
    ).returncode


def watch(args):
    return watch_mod.main()


def mark(args):
    return watch_mod.mark_main()


def build_parser():
    parser = argparse.ArgumentParser(
        prog="onepace",
        description="Unified CLI for the One Pace private streaming setup: "
                     "server provisioning, downloading, the watch progress TUI, "
                     "the episode ledger, and the fzf/IINA player.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    setup_parser = sub.add_parser("setup", help="provision a Mac client or the server")
    setup = setup_parser.add_subparsers(dest="setup_target", required=True)
    p = setup.add_parser("mac", help="install fzf + IINA and mount the share on this Mac")
    p.add_argument("samba_user", help="your Samba username on the server")
    p.set_defaults(func=setup_mac)
    setup.add_parser(
        "server", help="install + configure transmission-daemon and Samba on the server"
    ).set_defaults(func=setup_server)

    magnets_parser = sub.add_parser("magnets", help="manage the torrent queue on the server")
    magnets = magnets_parser.add_subparsers(dest="magnets_action", required=True)
    magnets.add_parser(
        "add", help="queue every magnet in data/dressrosaplus.csv on the server"
    ).set_defaults(func=magnets_add)

    ledger_parser = sub.add_parser("ledger", help="manage episodes.json")
    ledger = ledger_parser.add_subparsers(dest="ledger_action", required=True)
    ledger.add_parser(
        "refresh",
        help="rescan the server's files and merge them into episodes.json, "
             "preserving existing watched marks",
    ).set_defaults(func=ledger_refresh)

    p = sub.add_parser("progress", help="live-refreshing table of download progress")
    p.add_argument(
        "interval", type=int, nargs="?", default=8,
        help="refresh interval in seconds (default: 8)",
    )
    p.set_defaults(func=progress)

    sub.add_parser(
        "mount", help="mount the SMB share at /Volumes/onepace (idempotent)"
    ).set_defaults(func=watch_mod.mount)

    sub.add_parser(
        "watch", help="pick an episode via fzf, play it in IINA, mark it watched"
    ).set_defaults(func=watch)

    sub.add_parser(
        "mark", help="toggle watched/unwatched on one or more episodes via fzf, no playback"
    ).set_defaults(func=mark)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
