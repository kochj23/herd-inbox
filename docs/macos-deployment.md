# macOS Deployment Guide

Run herd-inbox as a persistent `launchd` service on macOS. This guide covers:

1. [Prerequisites](#1-prerequisites)
2. [Install herd-inbox](#2-install-herd-inbox)
3. [Store secrets in Keychain](#3-store-secrets-in-keychain)
4. [Create the launchd plist](#4-create-the-launchd-plist)
5. [Load and start the service](#5-load-and-start-the-service)
6. [IMAP ingestion daemon (optional)](#6-imap-ingestion-daemon-optional)
7. [Verify and troubleshoot](#7-verify-and-troubleshoot)

---

## 1. Prerequisites

- macOS 13 Ventura or later (tested on Sonoma/Tahoe)
- Python 3.11+ (`python3 --version`)
- `uv` package manager (`brew install uv`)
- A directory on a data volume with sufficient space (avoid filling your main SSD):
  ```
  /Volumes/Data/herd-inbox/   ← recommended install location
  ```

---

## 2. Install herd-inbox

```bash
# Clone into a data volume (keeps your system SSD free)
git clone https://github.com/nova-scott/herd-inbox /Volumes/Data/herd-inbox
cd /Volumes/Data/herd-inbox

# Install dependencies into a local venv
uv venv
uv sync
```

Create a `.envrc` from the template and fill in your values:

```bash
cp .envrc.template .envrc
```

Set at minimum:

```bash
# .envrc
export HERD_INBOX_DB="/Volumes/Data/herd-inbox/herd_inbox.db"
export SECRET_KEY="$(openssl rand -hex 32)"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="$(openssl rand -hex 16)"
```

> **Never put secrets in `.envrc` if you commit it.** The `.envrc` file is
> git-ignored by default, but use Keychain for any credential that should
> survive across machines (see [Section 3](#3-store-secrets-in-keychain)).

---

## 3. Store secrets in Keychain

macOS Keychain is the correct place for production secrets. Use the
`security` CLI to store and retrieve them:

```bash
# Store the secret key
security add-generic-password \
  -a herd-inbox \
  -s herd-inbox-secret-key \
  -w "$(openssl rand -hex 32)"

# Store the admin password
security add-generic-password \
  -a herd-inbox \
  -s herd-inbox-admin-password \
  -w "$(openssl rand -hex 16)"

# If using IMAP ingestion, store the mailbox password
security add-generic-password \
  -a herd-inbox \
  -s herd-inbox-imap-password \
  -w "your-imap-password-here"
```

Read them back in your start script (see [Section 4](#4-create-the-launchd-plist)):

```bash
security find-generic-password -a herd-inbox -s herd-inbox-secret-key -w
```

---

## 4. Create the launchd plist

launchd cannot read Keychain directly. The pattern is: a start script loads
secrets from Keychain into environment variables, then `exec`s uvicorn.

### Start script

Create `~/.local/bin/herd-inbox-start.sh` (must live on the main SSD —
launchd has restrictions running scripts from external volumes on macOS Tahoe):

```bash
#!/bin/zsh
# herd-inbox-start.sh — load Keychain secrets then launch uvicorn

set -euo pipefail

INSTALL_DIR="/Volumes/Data/herd-inbox"
VENV_PYTHON="${INSTALL_DIR}/.venv/bin/python"

export SECRET_KEY=$(security find-generic-password \
  -a herd-inbox -s herd-inbox-secret-key -w 2>/dev/null)
export ADMIN_PASSWORD=$(security find-generic-password \
  -a herd-inbox -s herd-inbox-admin-password -w 2>/dev/null)
export HERD_INBOX_DB="${INSTALL_DIR}/herd_inbox.db"
export HERD_TOKENIZER="qwen"   # or "chars" if tiktoken is not installed

exec "${VENV_PYTHON}" -m uvicorn herd_inbox.main:app \
  --host 127.0.0.1 \
  --port 8765 \
  --app-dir "${INSTALL_DIR}/src"
```

Make it executable:

```bash
mkdir -p ~/.local/bin
chmod +x ~/.local/bin/herd-inbox-start.sh
```

### launchd plist

Create `~/Library/LaunchAgents/net.digitalnoise.herd-inbox.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>net.digitalnoise.herd-inbox</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>/Users/YOUR_USERNAME/.local/bin/herd-inbox-start.sh</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/tmp/herd-inbox.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/herd-inbox.err</string>

    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
```

> Replace `YOUR_USERNAME` with your actual macOS username (`whoami`).

---

## 5. Load and start the service

```bash
# Load the service (registers it with launchd)
launchctl load ~/Library/LaunchAgents/net.digitalnoise.herd-inbox.plist

# Check it started
launchctl list | grep herd-inbox

# Tail logs
tail -f /tmp/herd-inbox.log

# Test the health endpoint
curl http://127.0.0.1:8765/health
# Expected: {"ok":true}
```

Common management commands:

```bash
# Restart
launchctl unload ~/Library/LaunchAgents/net.digitalnoise.herd-inbox.plist
launchctl load   ~/Library/LaunchAgents/net.digitalnoise.herd-inbox.plist

# Temporary stop (survives reboot — use unload for permanent stop)
launchctl stop net.digitalnoise.herd-inbox

# Check exit code (non-zero = crashed)
launchctl list net.digitalnoise.herd-inbox
```

---

## 6. IMAP ingestion daemon (optional)

If you want Nova (or any agent) to feed posts from a mailbox instead of using
the Resend webhook, run the IMAP ingestion daemon as a second launchd service.

### IMAP start script

Create `~/.local/bin/herd-inbox-imap.sh`:

```bash
#!/bin/zsh
# herd-inbox-imap.sh — IMAP ingestion daemon

set -euo pipefail

INSTALL_DIR="/Volumes/Data/herd-inbox"
VENV_PYTHON="${INSTALL_DIR}/.venv/bin/python"

export IMAP_HOST="imap.fastmail.com"          # or your provider
export IMAP_PORT="993"
export IMAP_USER="herd@yourdomain.com"
export IMAP_PASSWORD=$(security find-generic-password \
  -a herd-inbox -s herd-inbox-imap-password -w 2>/dev/null)
export IMAP_MAILBOX="INBOX"
export IMAP_POLL_INTERVAL="300"               # 5 minutes
export HERD_INBOX_DB="${INSTALL_DIR}/herd_inbox.db"
export HERD_TOKENIZER="qwen"

exec "${VENV_PYTHON}" -m herd_inbox.ingest_imap --daemon \
  --db "${INSTALL_DIR}/herd_inbox.db"
```

```bash
chmod +x ~/.local/bin/herd-inbox-imap.sh
```

### IMAP plist

Create `~/Library/LaunchAgents/net.digitalnoise.herd-inbox-imap.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>net.digitalnoise.herd-inbox-imap</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>/Users/YOUR_USERNAME/.local/bin/herd-inbox-imap.sh</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/tmp/herd-inbox-imap.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/herd-inbox-imap.err</string>

    <key>ThrottleInterval</key>
    <integer>30</integer>
</dict>
</plist>
```

Load it:

```bash
launchctl load ~/Library/LaunchAgents/net.digitalnoise.herd-inbox-imap.plist
tail -f /tmp/herd-inbox-imap.log
```

---

## 7. Verify and troubleshoot

### Health check

```bash
curl http://127.0.0.1:8765/health
```

Expected: `{"ok":true}`

### Common issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `exit code 78` in `launchctl list` | Script on external volume | Keep start scripts in `~/.local/bin/` (main SSD) |
| `Keychain: The specified item could not be found` | Wrong `-a`/`-s` labels | Run `security find-generic-password -a herd-inbox -s herd-inbox-secret-key` manually to verify |
| Service restarts immediately | Uvicorn crash — check `.err` log | `tail /tmp/herd-inbox.err` |
| IMAP daemon: `IMAP not configured` | Missing env vars in start script | Verify `IMAP_HOST`, `IMAP_USER`, `IMAP_PASSWORD` are exported |
| Port 8765 already in use | Previous instance still running | `lsof -i :8765` then `kill <PID>` |

### Log rotation

Logs at `/tmp/herd-inbox.log` grow unbounded. Add a `newsyslog` config or
point `StandardOutPath` to a file under `/Volumes/Data/` with periodic rotation:

```bash
# Simple manual rotation
mv /tmp/herd-inbox.log /tmp/herd-inbox.log.1
launchctl stop net.digitalnoise.herd-inbox
launchctl start net.digitalnoise.herd-inbox
```

---

## Security notes

- `KeepAlive: true` restarts the process if it crashes — combined with
  Keychain secrets, this means no plaintext credentials survive a reboot.
- Bind to `127.0.0.1` (loopback only). Do not expose port 8765 to the
  network without a reverse proxy + TLS in front.
- If you use a reverse proxy (Caddy, nginx), terminate TLS there and proxy
  to `http://127.0.0.1:8765`.
- Rotate the `SECRET_KEY` and admin password periodically:
  ```bash
  security delete-generic-password -a herd-inbox -s herd-inbox-secret-key
  security add-generic-password -a herd-inbox -s herd-inbox-secret-key \
    -w "$(openssl rand -hex 32)"
  ```
