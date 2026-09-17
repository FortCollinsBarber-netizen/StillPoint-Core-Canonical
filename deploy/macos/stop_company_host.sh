#!/bin/zsh
set -euo pipefail
LABEL="com.stillpoint.company"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"
/bin/launchctl bootout "$DOMAIN" "$PLIST" 2>/dev/null || true
echo "StillPoint company supervisor unloaded. Durable company state was preserved."
