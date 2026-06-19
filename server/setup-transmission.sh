#!/usr/bin/env bash
set -euo pipefail
# Run from the Mac. Installs + configures transmission-daemon on $SERVER.
# Uses `ssh -t` for any step that needs sudo, so the password prompt works
# over the SSH session (sudo has no tty otherwise).

SERVER="${ONEPACE_SERVER:-server-node-0}"
REMOTE_USER=$(ssh $SERVER "whoami")
echo "Remote user: $REMOTE_USER"

# 1. Install (Debian/Ubuntu).
ssh -t $SERVER "sudo apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y transmission-daemon"

# 2. Stop the daemon before editing config (it overwrites settings.json on shutdown).
ssh -t $SERVER "sudo systemctl stop transmission-daemon"

# 3. Create download dirs owned by the service user (debian-transmission by default).
ssh $SERVER "mkdir -p /home/$REMOTE_USER/onepace/.incomplete"

# 4. Push our settings.json (substituting the user). Staged via a plain (non-sudo)
#    write to /tmp first, then moved into place with sudo -- piping the file content
#    straight into `sudo tee` over ssh breaks if sudo needs a password, since sudo's
#    own prompt and the piped content fight over the same stdin.
sed "s/__USER__/$REMOTE_USER/g" server/settings.json | ssh $SERVER "cat > /tmp/td-settings.json"
ssh -t $SERVER "sudo mv /tmp/td-settings.json /etc/transmission-daemon/settings.json"

# 5. Let the transmission service user reach the download dir. Only `o+x` (search/traversal)
#    on the home dir itself -- group/other WRITE on a home dir trips sshd's StrictModes check
#    and silently disables key-based auth, forcing password-only login.
ssh -t $SERVER "sudo usermod -aG $REMOTE_USER debian-transmission || true; \
  sudo chmod o+x /home/$REMOTE_USER; \
  sudo chmod 775 /home/$REMOTE_USER/onepace"

# 6. Override Type=notify -> Type=simple. The Ubuntu transmission-daemon build never calls
#    sd_notify(), so a Type=notify unit always times out (~90s) waiting for a ready signal
#    that never arrives, even though the daemon is already up and serving RPC.
ssh $SERVER "cat > /tmp/td-override.conf << 'EOF'
[Service]
Type=simple
EOF"
ssh -t $SERVER "sudo mkdir -p /etc/systemd/system/transmission-daemon.service.d && \
  sudo mv /tmp/td-override.conf /etc/systemd/system/transmission-daemon.service.d/override.conf && \
  sudo systemctl daemon-reload"

# 7. Start + enable on boot.
ssh -t $SERVER "sudo systemctl reset-failed transmission-daemon || true; \
  sudo systemctl enable transmission-daemon && sudo systemctl start transmission-daemon"
sleep 2
ssh $SERVER "systemctl is-active transmission-daemon && transmission-remote -l"
echo "transmission-daemon is up."
