#!/bin/bash
set -euo pipefail
LABEL="com.stillpoint.signal-mail"
DOMAIN="gui/$(id -u)"
LOGDIR="$HOME/Library/Logs/StillPoint"

echo "==> launchd"
/bin/launchctl print "$DOMAIN/$LABEL" 2>/dev/null || echo "Signal LaunchAgent is not loaded."

echo
echo "==> recent stdout"
tail -n 40 "$LOGDIR/signal-mail.out.log" 2>/dev/null || true

echo
echo "==> recent stderr"
tail -n 40 "$LOGDIR/signal-mail.err.log" 2>/dev/null || true
