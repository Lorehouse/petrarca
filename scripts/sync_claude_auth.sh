#!/bin/bash
# Sync Claude OAuth credentials to Hetzner server.
# Reads from ~/.claude-accounts/personal.json (stable snapshot maintained by
# the claude-use fish function) rather than keychain, so local account swaps
# never leak non-personal creds to the server.
# Run via launchd every 4 hours to keep server auth fresh.

set -euo pipefail

CREDS=$(cat "$HOME/.claude-accounts/personal.json" 2>/dev/null) || {
    echo "$(date): No personal snapshot at ~/.claude-accounts/personal.json" >> /tmp/claude-auth-sync.log
    exit 1
}

# Verify token is valid before pushing
EXPIRES=$(echo "$CREDS" | python3 -c "import json,sys,time; d=json.loads(sys.stdin.read()); print(d.get('claudeAiOauth',{}).get('expiresAt',0))")
NOW_MS=$(python3 -c "import time; print(int(time.time()*1000))")

if [ "$EXPIRES" -le "$NOW_MS" ]; then
    echo "$(date): Local token expired, skipping sync" >> /tmp/claude-auth-sync.log
    exit 0
fi

# Push to server
echo "$CREDS" | ssh alif "cat > /root/.claude/.credentials.json && chmod 600 /root/.claude/.credentials.json"

echo "$(date): Synced credentials (expires $(python3 -c "from datetime import datetime; print(datetime.fromtimestamp($EXPIRES/1000))"))" >> /tmp/claude-auth-sync.log
