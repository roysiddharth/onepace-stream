#!/usr/bin/env bash
# Live-refreshing table view of all torrents, refreshing every INTERVAL seconds.
# Queries the transmission RPC API directly (instead of `-t all -i`'s verbose
# per-torrent dump) so the output can be rendered as a clean, aligned table.
set -euo pipefail

INTERVAL="${1:-8}"
SERVER="${ONEPACE_SERVER:-server-node-0}"

while true; do
  OUTPUT=$(ssh "$SERVER" bash -s <<'REMOTE' | column -t -s $'\t'
set -euo pipefail
SID=$(curl -s -o /dev/null -D - http://localhost:9091/transmission/rpc \
  | awk -F': ' '/^X-Transmission-Session-Id:/{print $2}' | tr -d '\r')
curl -s -H "X-Transmission-Session-Id: $SID" \
  -d '{"method":"torrent-get","arguments":{"fields":["name","percentDone","eta","rateDownload","rateUpload","status","peersConnected"]}}' \
  http://localhost:9091/transmission/rpc \
| jq -r '
  def human_rate:
    if . == 0 then "-"
    elif . < 1024 then "\(.)B/s"
    elif . < 1048576 then "\(. / 1024 | floor)KB/s"
    else "\(. / 1048576 * 10 | floor / 10)MB/s"
    end;
  def status_name:
    if . == 0 then "Stopped"
    elif . == 1 then "QueueCheck"
    elif . == 2 then "Checking"
    elif . == 3 then "QueueDL"
    elif . == 4 then "Downloading"
    elif . == 5 then "QueueSeed"
    elif . == 6 then "Seeding"
    else "Unknown"
    end;
  ["NAME","DONE%","STATUS","DOWN","UP","ETA","PEERS"],
  (.arguments.torrents[] | [
      (.name | if length > 40 then .[0:37] + "..." else . end),
      ((.percentDone * 100 | floor | tostring) + "%"),
      (.status | status_name),
      (.rateDownload | human_rate),
      (.rateUpload | human_rate),
      (if .eta < 0 then "-" else (.eta | tostring) + "s" end),
      (.peersConnected | tostring)
  ])
  | @tsv
'
REMOTE
)
  printf '\033[H\033[2J\033[3J'
  echo "$OUTPUT"
  date "+updated: %H:%M:%S"
  sleep "$INTERVAL"
done
