#!/bin/zsh
set -euo pipefail
APP="$HOME/Library/Application Support/StillPoint"
echo "==> launchd"
launchctl print "gui/$(id -u)/com.stillpoint.company" 2>&1 \
  | grep -E 'state =|pid =|runs =|last exit code|last terminating signal' | head -20 || true
echo
echo "==> stillpointd status cache"
"$APP/bin/run_company.sh" status || true
