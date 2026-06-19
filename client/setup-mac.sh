#!/usr/bin/env bash
set -euo pipefail
# Run on EACH Mac (Air and Pro). Idempotent.

SHARE_USER="${1:-}"
TS_IP="${2:-${ONEPACE_HOST:-}}"
if [ -z "$SHARE_USER" ] || [ -z "$TS_IP" ]; then
  echo "usage: bash client/setup-mac.sh <samba-username> <server-tailnet-ip>"
  echo "       (or set ONEPACE_HOST and pass just <samba-username>)"
  exit 2
fi

# 1. Install fzf + IINA if missing (Homebrew).
command -v brew >/dev/null || { echo "Install Homebrew first: https://brew.sh"; exit 1; }
command -v fzf >/dev/null || brew install fzf
command -v iina >/dev/null || brew install --cask iina   # cask symlinks the CLI as `iina`, not `iina-cli`

# 2. Enable IINA's resume-on-quit (mpv watch-later) explicitly.
mkdir -p "$HOME/.config/mpv"
grep -q 'save-position-on-quit' "$HOME/.config/mpv/mpv.conf" 2>/dev/null || \
  printf 'save-position-on-quit=yes\nresume-playback=yes\n' >> "$HOME/.config/mpv/mpv.conf"

# 3. Mount the SMB share at the FIXED path (IINA resume is path-keyed).
mkdir -p /Volumes/onepace
mount | grep -q '/Volumes/onepace' || \
  mount_smbfs "//$SHARE_USER@$TS_IP/onepace" /Volumes/onepace || \
  open "smb://$TS_IP/onepace"

ls /Volumes/onepace >/dev/null && echo "Mounted /Volumes/onepace OK; fzf + iina ready."
