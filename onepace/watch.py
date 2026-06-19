"""Interactive launcher: pick an episode via fzf, play in IINA, mark watched.

Usage: python3 -m onepace.watch
Env:   ONEPACE_ROOT        (mount root, default /Volumes/onepace)
       ONEPACE_LEDGER      (path to episodes.json, default ./episodes.json)
       ONEPACE_SAMBA_USER  (Samba username on the server; required to mount)
       ONEPACE_HOST        (server's tailnet IP/hostname; required to mount)
"""
import os
import subprocess
import sys

from onepace import ledger

ROOT = os.environ.get("ONEPACE_ROOT", "/Volumes/onepace")
LEDGER = os.environ.get("ONEPACE_LEDGER", "episodes.json")
SAMBA_USER = os.environ.get("ONEPACE_SAMBA_USER", "")
SAMBA_HOST = os.environ.get("ONEPACE_HOST", "")  # server's tailnet IP/hostname


def mount(_args=None):
    """Mount the SMB share at ROOT. Idempotent; prompts for sudo + Samba passwords."""
    if os.path.ismount(ROOT):
        print(f"already mounted: {ROOT}")
        return 0
    if not SAMBA_USER or not SAMBA_HOST:
        print("set ONEPACE_SAMBA_USER and ONEPACE_HOST (the server's tailnet "
              "user/IP) before mounting.")
        return 1
    # ponytail: /Volumes is root-owned, so mkdir + chown need sudo; mount_smbfs
    # then runs as us onto a dir we own (root-owned dir => "Operation not permitted").
    subprocess.run(["sudo", "mkdir", "-p", ROOT], check=True)
    subprocess.run(["sudo", "chown", os.getlogin(), ROOT], check=True)
    rc = subprocess.run(["mount_smbfs", f"//{SAMBA_USER}@{SAMBA_HOST}/onepace", ROOT]).returncode
    if rc == 0:
        print(f"mounted: {ROOT}")
    return rc


def label(e):
    return f"{e['arc']} {e['label']}"


def build_menu(entries, nxt):
    """Return fzf input lines as 'index<TAB>display'. index is int or 'next'."""
    lines = []
    if nxt is not None:
        lines.append(f"next\t▶  NEXT UP — {label(entries[nxt])}")
    for i, e in enumerate(entries):
        mark = "✓" if e["watched"] else "·"
        lines.append(f"{i}\t{mark}  {label(e)}")
    return lines


def pick(lines, prompt="one pace> ", multi=False):
    """Run fzf; return the selected index token(s) ('next' or str(int)) or None."""
    args = ["fzf", "--delimiter", "\t", "--with-nth", "2..",
            "--prompt", prompt, "--height", "90%", "--reverse"]
    if multi:
        args.append("--multi")
    proc = subprocess.run(
        args, input="\n".join(lines), capture_output=True, text=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    tokens = [line.split("\t", 1)[0] for line in proc.stdout.strip().splitlines()]
    return tokens if multi else tokens[0]


def main():
    entries = ledger.load(LEDGER)
    nxt = ledger.next_unwatched(entries)
    token = pick(build_menu(entries, nxt))
    if token is None:
        print("nothing selected.")
        return 0
    index = nxt if token == "next" else int(token)
    if index is None:
        print("everything is watched. 🎉")
        return 0

    entry = entries[index]
    path = os.path.join(ROOT, entry["relpath"])
    if not os.path.exists(path):
        if not os.path.ismount(ROOT):
            print(f"{ROOT} not mounted — mounting…")
            mount()
        if not os.path.exists(path):
            print(f"file not found: {path}\nis {ROOT} mounted?")
            return 1

    print(f"▶ playing: {label(entry)}")
    # `open -a IINA` (not the iina/iina-cli binary) — the bare binary can't read
    # the SMB network mount when invoked directly from Terminal (TCC quirk).
    # If IINA is already running idle, `open -a` just refocuses its welcome
    # window instead of loading the new file, so force a clean launch first.
    # It also hands off to the GUI app and returns immediately (non-blocking),
    # so we gate marking on a manual prompt instead of waiting for the process.
    subprocess.run(["killall", "IINA"], stderr=subprocess.DEVNULL)
    subprocess.run(["open", "-a", "IINA", path])
    ans = input(f'mark "{label(entry)}" as watched? [y/N]: ').strip().lower()
    if ans == "y":
        ledger.mark_watched(entries, index)
        ledger.save(LEDGER, entries)
        nxt2 = ledger.next_unwatched(entries)
        up = label(entries[nxt2]) if nxt2 is not None else "— series complete 🎉"
        print(f"marked watched. next up: {up}")
    else:
        print("left unwatched (IINA will resume where you stopped).")
    return 0


def mark_main():
    """Toggle watched/unwatched on one or more episodes via fzf, no playback."""
    entries = ledger.load(LEDGER)
    lines = [f"{i}\t{'✓' if e['watched'] else '·'}  {label(e)}" for i, e in enumerate(entries)]
    tokens = pick(lines, prompt="toggle watched> ", multi=True)
    if not tokens:
        print("nothing selected.")
        return 0

    for token in tokens:
        index = int(token)
        ledger.toggle_watched(entries, index)
        state = "watched" if entries[index]["watched"] else "unwatched"
        print(f"marked {state}: {label(entries[index])}")
    ledger.save(LEDGER, entries)

    nxt = ledger.next_unwatched(entries)
    up = label(entries[nxt]) if nxt is not None else "— series complete 🎉"
    print(f"next up: {up}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
