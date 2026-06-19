#!/usr/bin/env bash
set -euo pipefail
# Run from the Mac. Adds every magnet in data/dressrosaplus.csv to the remote daemon.

SERVER="${ONEPACE_SERVER:-server-node-0}"
CSV="${1:-data/dressrosaplus.csv}"
count=0
# Skip header; field 3 is the magnet.
while IFS=, read -r arc number magnet rest; do
  [ "$arc" = "arc" ] && continue            # header
  [ -z "${magnet:-}" ] && continue
  magnet="${magnet%\"}"; magnet="${magnet#\"}"   # strip accidental quotes
  ssh -n $SERVER "transmission-remote -a '$magnet'" >/dev/null
  count=$((count+1))
  echo "added: $arc $number"
done < "$CSV"
echo "queued $count torrents"
ssh $SERVER "transmission-remote -l | tail -n +1 | head -20"