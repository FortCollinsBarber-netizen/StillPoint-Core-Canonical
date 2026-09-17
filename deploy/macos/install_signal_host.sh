#!/bin/bash
set -euo pipefail

REPO="FortCollinsBarber-netizen/StillPoint-Core-Canonical"
APP_SUPPORT="$HOME/Library/Application Support/StillPoint"
CORE="$APP_SUPPORT/Core"
RUNTIME="$APP_SUPPORT/Runtime"
VENV="$APP_SUPPORT/venv"
BIN="$APP_SUPPORT/bin"
LOGDIR="$HOME/Library/Logs/StillPoint"
PLIST="$HOME/Library/LaunchAgents/com.stillpoint.signal-mail.plist"

ICLOUD_SERVICE="com.stillpoint.signal.icloud-app-password"
XAI_SERVICE="com.stillpoint.signal.xai-api-key"
ACCOUNT="$(id -un)"
APPROVED="abbada7549a95510d9552441a4f7bb1c92977f899cdfa953e8e394b058d00cc9"

die(){ echo "ERROR: $*" >&2; exit 1; }

command -v git >/dev/null || die "git is required"
command -v gh >/dev/null || die "GitHub CLI (gh) is required"
command -v security >/dev/null || die "macOS security CLI is required"

PYTHON_BIN="${STILLPOINT_PYTHON:-/opt/homebrew/opt/python@3.13/libexec/bin/python3}"
test -x "$PYTHON_BIN" || die "Python 3.13 not found at $PYTHON_BIN"

mkdir -p "$APP_SUPPORT" "$RUNTIME/state" "$BIN" "$LOGDIR" "$HOME/Library/LaunchAgents"

echo "==> Install/update canonical source"
if [ ! -d "$CORE/.git" ]; then
  git clone "https://github.com/$REPO.git" "$CORE"
else
  git -C "$CORE" fetch origin main --prune
fi
git -C "$CORE" checkout main
git -C "$CORE" reset --hard origin/main

PATCH_ID="$("$PYTHON_BIN" - "$CORE" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1])
print(json.loads((root/"RELEASE_MANIFEST.json").read_text())["patch"])
PY
)"
test "$PATCH_ID" = "038-production-host-closure" || die "canonical main is not Patch 038; found $PATCH_ID"

COMMIT="$(git -C "$CORE" rev-parse HEAD)"
echo "Canonical commit: $COMMIT"

echo "==> Verify canonical merge CI"
RUN_JSON="$(gh run list --repo "$REPO" --commit "$COMMIT" --workflow "StillPoint Core CI" --event push --limit 5 --json databaseId,status,conclusion,headSha --jq '.[0]')"
test -n "$RUN_JSON" && test "$RUN_JSON" != "null" || die "no push CI found for canonical commit"
CI_STATUS="$(printf '%s' "$RUN_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
CI_CONCLUSION="$(printf '%s' "$RUN_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["conclusion"])')"
test "$CI_STATUS" = "completed" && test "$CI_CONCLUSION" = "success" || die "canonical CI is not green"

echo "==> Build isolated runtime environment"
rm -rf "$VENV"
"$PYTHON_BIN" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install "$CORE"

install -m 700 "$CORE/deploy/macos/run_signal_mail.sh" "$BIN/run_signal_mail.sh"
install -m 700 "$CORE/deploy/macos/status_signal_host.sh" "$BIN/status_signal_host.sh"
install -m 700 "$CORE/deploy/macos/stop_signal_host.sh" "$BIN/stop_signal_host.sh"

store_secret () {
  local service="$1"
  local prompt="$2"
  if /usr/bin/security find-generic-password -a "$ACCOUNT" -s "$service" -w >/dev/null 2>&1 && [ "${STILLPOINT_RESET_SECRETS:-0}" != "1" ]; then
    echo "Keychain item already present: $service"
    return
  fi
  local secret=""
  read -r -s -p "$prompt" secret
  echo
  test -n "$secret" || die "empty secret refused"
  /usr/bin/security add-generic-password -U -a "$ACCOUNT" -s "$service" -w "$secret" >/dev/null
  unset secret
}

echo "==> Store secrets in login Keychain"
store_secret "$ICLOUD_SERVICE" "Paste the Apple app-specific password for StillPoint Signal (input hidden): "
store_secret "$XAI_SERVICE" "Paste the xAI API key for StillPoint Signal (input hidden): "

echo "==> Provision exact approved governance (no external action)"
export STILLPOINT_ROOT="$RUNTIME"
export STILLPOINT_SOURCE_ROOT="$CORE"
"$VENV/bin/python" "$CORE/deploy/macos/provision_signal_governance.py"

echo "==> Install LaunchAgent wrapper"
cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.stillpoint.signal-mail</string>
  <key>ProgramArguments</key>
  <array>
    <string>$BIN/run_signal_mail.sh</string>
    <string>serve</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>ThrottleInterval</key>
  <integer>60</integer>
  <key>ProcessType</key>
  <string>Background</string>
  <key>StandardOutPath</key>
  <string>$LOGDIR/signal-mail.out.log</string>
  <key>StandardErrorPath</key>
  <string>$LOGDIR/signal-mail.err.log</string>
</dict>
</plist>
PLIST
chmod 600 "$PLIST"
/usr/bin/plutil -lint "$PLIST" >/dev/null

echo "==> Interactive Keychain/readiness preflight"
"$BIN/run_signal_mail.sh" check

echo "==> Activate approved per-user Signal LaunchAgent"
DOMAIN="gui/$(id -u)"
/bin/launchctl bootout "$DOMAIN" "$PLIST" 2>/dev/null || true
/bin/launchctl bootstrap "$DOMAIN" "$PLIST"
/bin/launchctl kickstart -k "$DOMAIN/com.stillpoint.signal-mail"

echo
echo "PRODUCTION SIGNAL ACTIVATED"
echo "Canonical commit: $COMMIT"
echo "Governance SHA-256: $APPROVED"
echo "Mailbox: fortcollinsbarber@icloud.com"
echo "Jurisdiction: personal_business"
echo "LaunchAgent: com.stillpoint.signal-mail"
echo "Status command: $BIN/status_signal_host.sh"
echo "Stop command:   $BIN/stop_signal_host.sh"
