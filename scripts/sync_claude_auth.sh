#!/bin/bash
# Sync Claude OAuth credentials to Hetzner server.
# Reads from macOS keychain (where Claude Code stores live tokens),
# falling back to ~/.claude-accounts/personal.json snapshot.
# Run via launchd every 2 hours to keep server auth fresh.

set -euo pipefail
LOG="/tmp/claude-auth-sync.log"

# Try keychain first (Claude Code updates this on token refresh)
CREDS=$(security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null) || CREDS=""

if [ -z "$CREDS" ]; then
    # Fallback to snapshot file
    CREDS=$(cat "$HOME/.claude-accounts/personal.json" 2>/dev/null) || {
        echo "$(date): No credentials in keychain or snapshot file" >> "$LOG"
        exit 1
    }
    SOURCE="snapshot"
else
    SOURCE="keychain"
fi

# Verify token is valid before pushing
EXPIRES=$(echo "$CREDS" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('claudeAiOauth',{}).get('expiresAt',0))")
NOW_MS=$(python3 -c "import time; print(int(time.time()*1000))")

if [ "$EXPIRES" -le "$NOW_MS" ]; then
    echo "$(date): Token expired (source=$SOURCE), skipping sync" >> "$LOG"
    exit 0
fi

# Push to server
echo "$CREDS" | ssh alif "cat > /root/.claude/.credentials.json && chmod 600 /root/.claude/.credentials.json"

EXPIRES_HR=$(python3 -c "from datetime import datetime; print(datetime.fromtimestamp($EXPIRES/1000).strftime('%Y-%m-%d %H:%M'))")
echo "$(date): Synced from $SOURCE (expires $EXPIRES_HR)" >> "$LOG"
