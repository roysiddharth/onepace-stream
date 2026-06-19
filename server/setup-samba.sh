#!/usr/bin/env bash
set -euo pipefail
# Run from the Mac. Installs Samba and shares the onepace dir on the Tailscale interface only.

SERVER="${ONEPACE_SERVER:-server-node-0}"
REMOTE_USER=$(ssh $SERVER "whoami")

# 1. Install samba.
ssh -t $SERVER "sudo apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y samba"

# 2. Append a share definition bound to the tailnet only (idempotent: skip if present).
#    Staged via a plain (non-sudo) write to /tmp first, then appended with sudo --
#    piping the heredoc straight into `sudo tee` over ssh breaks if sudo needs a
#    password, since sudo's own prompt and the piped content fight over stdin.
ssh $SERVER "cat > /tmp/td-share.conf" <<EOF

[onepace]
   path = /home/$REMOTE_USER/onepace
   browseable = yes
   read only = yes
   guest ok = no
   valid users = $REMOTE_USER
   hosts allow = 100.64.0.0/10 127.0.0.1
   hosts deny = 0.0.0.0/0
EOF
ssh -t $SERVER "grep -q '\[onepace\]' /etc/samba/smb.conf || (cat /tmp/td-share.conf | sudo tee -a /etc/samba/smb.conf >/dev/null); rm -f /tmp/td-share.conf"

# 3. Bind smbd to loopback + tailscale interface only.
ssh -t $SERVER "sudo grep -q 'interfaces = ' /etc/samba/smb.conf || sudo sed -i '/\[global\]/a \   interfaces = lo tailscale0\n   bind interfaces only = yes' /etc/samba/smb.conf"

# 4. Set a Samba password for the user (interactive once; prompts on the server via ssh -t).
echo 'Set a Samba password for the share (used on the Macs):'
ssh -t $SERVER "sudo smbpasswd -a $REMOTE_USER"

# 5. Restart + verify.
ssh -t $SERVER "sudo systemctl restart smbd && sudo systemctl enable smbd"
ssh $SERVER "testparm -s 2>/dev/null | grep -A8 '\[onepace\]'"
echo 'Samba share [onepace] is up on the tailnet.'