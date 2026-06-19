# onepace-stream

A small, self-hosted toolkit for running your **own** private media library over
[Tailscale](https://tailscale.com): a headless Linux box downloads via
`transmission-daemon` and shares over Samba/SMB; your Macs mount the share and
play episodes in order through a tiny `fzf` + IINA launcher with per-device
"resume where I left off" progress.

It was written around the [One Pace](https://onepace.net) fan edit, but it ships
**no content and no links to content**. You point it at releases you have
lawfully acquired yourself; the tool just automates the plumbing
(download → share → ledger → play).

> **You provide the content.** This repo contains code only. No torrents, no
> magnet links, no media. See [Bring your own content](#bring-your-own-content).

## Requirements

- **Server:** a Debian/Ubuntu host reachable over your tailnet, with SSH access
  (an entry in `~/.ssh/config`, e.g. a host alias). Needs `sudo`.
- **Mac client(s):** Homebrew, plus `fzf` and IINA (the setup script installs both).
- **Both:** Tailscale already up on every machine.

## Configuration

Everything is driven by environment variables — no hardcoded hosts or paths:

| Variable | Meaning | Default |
| --- | --- | --- |
| `ONEPACE_SERVER` | SSH target for the server (host alias or `user@host`) | `server-node-0` |
| `ONEPACE_HOST` | Server's tailnet IP/hostname (used to mount the SMB share) | — (required to mount) |
| `ONEPACE_SAMBA_USER` | Your Samba username on the server | — (required to mount) |
| `ONEPACE_ROOT` | Local mount point on each Mac | `/Volumes/onepace` |
| `ONEPACE_LEDGER` | Path to the episode ledger JSON | `./episodes.json` |

Set `ONEPACE_SERVER` to match your own SSH host before running anything, e.g.:

```bash
export ONEPACE_SERVER="me@100.x.y.z"
```

## CLI

Everything is driven through the `onepace` CLI (`python3 -m onepace <command>`
from the repo root). Run `onepace --help` or `onepace <command> --help` for details.

| Command | Description |
| --- | --- |
| `onepace setup server` | install + configure transmission-daemon and Samba on the server |
| `onepace setup mac <samba-user>` | install fzf + IINA and mount the share on this Mac |
| `onepace magnets add` | queue every magnet in `data/dressrosaplus.csv` on the server |
| `onepace progress [interval]` | live-refreshing TUI table of download progress (default refresh: 8s) |
| `onepace ledger refresh` | rescan the server's files into `episodes.json`, preserving existing watched marks |
| `onepace watch` | pick an episode via fzf, play it in IINA, mark it watched |

### Global `onepace` command

To run `onepace` from any directory, add a thin wrapper to a directory on your
`PATH`, e.g. `~/.local/bin/onepace`:

```bash
#!/usr/bin/env bash
exec env PYTHONPATH="/path/to/onepace-stream:${PYTHONPATH:-}" python3 -m onepace "$@"
```

`chmod +x` it, and `onepace <command>` works from anywhere.

## Bring your own content

This repo intentionally **does not include** a magnet catalog. Create your own
`data/dressrosaplus.csv` from a copy of the provided template:

```bash
cp data/dressrosaplus.example.csv data/dressrosaplus.csv
```

Then fill in the `magnet` column with links to releases **you have lawfully
acquired the right to download**. The columns are
`arc,number,magnet,release_type,quality`. This file is git-ignored so your
catalog never ends up in version control.

## Usage

### One-time server setup (run from this repo on the Mac)
1. `onepace setup server`   # install + configure transmission-daemon + Samba
2. Fill in `data/dressrosaplus.csv` (see above)
3. `onepace magnets add`    # queue everything in your CSV
4. Watch progress: `onepace progress`
5. Build the ledger: `onepace ledger refresh` → produces `episodes.json`

### Per-Mac setup
1. `onepace setup mac <samba-user>`      # mount the share, install fzf + IINA
2. Copy `episodes.json` next to `onepace/` (one canonical copy; each Mac tracks
   its own watched state)

### Watch
`onepace watch`                          # Enter = next unwatched; type to jump

## Notes
- RPC and Samba bind to loopback + the Tailscale interface only — nothing is
  exposed on a public NIC.
- Seeding stops the moment each download completes (ratio 0).
- IINA resume is keyed to the absolute file path, so the mount point must be
  identical and stable across Macs (hence the fixed `ONEPACE_ROOT`).

## Legal

This project is a downloader/orchestrator. It contains no media and no links to
media. You are responsible for ensuring you have the legal right to download and
store any content you point it at. One Piece and One Pace are the property of
their respective rights holders; this project is not affiliated with or endorsed
by them.

## License

MIT — see [LICENSE](LICENSE).
