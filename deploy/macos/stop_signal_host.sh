#!/bin/bash
set -euo pipefail
LABEL="com.stillpoint.signal-mail"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"
/bin/launchctl bootout "$DOMAIN" "$PLIST" 2>/dev/null || true
echo "Signal LaunchAgent unloaded. Governance and durable state were preserved."
