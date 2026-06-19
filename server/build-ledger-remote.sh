#!/usr/bin/env bash
set -euo pipefail
# Run from the Mac. Builds episodes.json from the real files on $SERVER
# in one shot: push build_ledger.py + arc_order.txt, scan remotely, pull the
# result back to ./episodes.json. Avoids manual scp/ssh/scp round trips.

cd "$(dirname "$0")/.."

SERVER="${ONEPACE_SERVER:-server-node-0}"
REMOTE_USER=$(ssh $SERVER "whoami")
REMOTE_TMP="/tmp/onepace-build-ledger"

ssh $SERVER "mkdir -p $REMOTE_TMP"
scp -q onepace/build_ledger.py data/arc_order.txt "$SERVER:$REMOTE_TMP/"

ssh $SERVER "python3 $REMOTE_TMP/build_ledger.py /home/$REMOTE_USER/onepace $REMOTE_TMP/arc_order.txt $REMOTE_TMP/episodes.json"

scp -q "$SERVER:$REMOTE_TMP/episodes.json" ./episodes.fresh.json

python3 -c "
from onepace import ledger
import os
fresh = ledger.load('episodes.fresh.json')
if os.path.exists('episodes.json'):
    fresh = ledger.merge_watched(ledger.load('episodes.json'), fresh)
ledger.save('episodes.json', fresh)
os.remove('episodes.fresh.json')
print(f'episodes.json: {len(fresh)} episodes, first = {fresh[0][\"arc\"]} {fresh[0][\"label\"]}')
"
