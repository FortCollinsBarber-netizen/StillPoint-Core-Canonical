#!/bin/bash
set -euo pipefail

REPO="FortCollinsBarber-netizen/StillPoint-Core-Canonical"
APP="$HOME/Library/Application Support/StillPoint"
CORE="$APP/Core"
RUNTIME="$APP/Runtime"
VENV="$APP/venv"
BIN="$APP/bin"
LOGDIR="$HOME/Library/Logs/StillPoint"
PLIST="$HOME/Library/LaunchAgents/com.stillpoint.company.plist"
XAI_SERVICE="com.stillpoint.provider.xai-api-key"
ACCOUNT="$(id -un)"
PYTHON_BIN="${STILLPOINT_PYTHON:-/opt/homebrew/opt/python@3.13/libexec/bin/python3}"

die(){ echo "ERROR: $*" >&2; exit 1; }

for cmd in git gh security; do command -v "$cmd" >/dev/null || die "$cmd is required"; done
test -x "$PYTHON_BIN" || die "Python 3.13 not found at $PYTHON_BIN"

mkdir -p "$APP" "$RUNTIME/state" "$BIN" "$LOGDIR" "$HOME/Library/LaunchAgents"

echo "==> Install/update canonical 0.4 source"
if [ ! -d "$CORE/.git" ]; then
  git clone "https://github.com/$REPO.git" "$CORE"
else
  git -C "$CORE" fetch origin main --prune
fi
git -C "$CORE" checkout main
git -C "$CORE" reset --hard origin/main

VERSION="$("$PYTHON_BIN" - "$CORE" <<'PY'
import re,sys
from pathlib import Path
text=(Path(sys.argv[1])/"pyproject.toml").read_text()
print(re.search(r'^version\s*=\s*"([^"]+)"',text,re.M).group(1))
PY
)"
test "$VERSION" = "0.4.0a1" || die "canonical main is not StillPoint 0.4 alpha; found $VERSION"

COMMIT="$(git -C "$CORE" rev-parse HEAD)"
echo "Canonical commit: $COMMIT"

echo "==> Verify canonical push CI"
RUN_JSON="$(gh run list --repo "$REPO" --commit "$COMMIT" --workflow "StillPoint Core CI" --event push --limit 5 --json databaseId,status,conclusion,headSha --jq '.[0]')"
test -n "$RUN_JSON" && test "$RUN_JSON" != "null" || die "no push CI found for canonical commit"
CI_STATUS="$(printf '%s' "$RUN_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
CI_CONCLUSION="$(printf '%s' "$RUN_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["conclusion"])')"
test "$CI_STATUS" = "completed" && test "$CI_CONCLUSION" = "success" || die "canonical CI is not green"

echo "==> Build isolated runtime"
rm -rf "$VENV"
"$PYTHON_BIN" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install "$CORE"

install -m 700 "$CORE/deploy/macos/run_company.sh" "$BIN/run_company.sh"
install -m 700 "$CORE/deploy/macos/status_company_host.sh" "$BIN/status_company_host.sh"
install -m 700 "$CORE/deploy/macos/stop_company_host.sh" "$BIN/stop_company_host.sh"

if ! /usr/bin/security find-generic-password -a "$ACCOUNT" -s "$XAI_SERVICE" -w >/dev/null 2>&1; then
  echo
  read -r -s -p "Paste xAI API key for StillPoint company runtime (input hidden): " SECRET
  echo
  test -n "$SECRET" || die "empty secret refused"
  /usr/bin/security add-generic-password -U -a "$ACCOUNT" -s "$XAI_SERVICE" -w "$SECRET" >/dev/null
  unset SECRET
fi

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.stillpoint.company</string>
  <key>ProgramArguments</key>
  <array><string>$BIN/run_company.sh</string><string>serve</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>ProcessType</key><string>Background</string>
  <key>StandardOutPath</key><string>$LOGDIR/company.out.log</string>
  <key>StandardErrorPath</key><string>$LOGDIR/company.err.log</string>
</dict>
</plist>
PLIST
chmod 600 "$PLIST"
/usr/bin/plutil -lint "$PLIST" >/dev/null

echo "==> Runtime structural preflight"
"$BIN/run_company.sh" check

echo "==> Live xAI credential/model capability preflight"
/usr/bin/security find-generic-password -a "$ACCOUNT" -s "$XAI_SERVICE" -w \
  | "$VENV/bin/python" "$CORE/deploy/macos/probe_xai_access.py" --model "grok-4.6" \
  || die "xAI credential/model capability preflight failed"

echo "==> Activate StillPoint company supervisor"
DOMAIN="gui/$(id -u)"
/bin/launchctl bootout "$DOMAIN" "$PLIST" 2>/dev/null || true
/bin/launchctl bootstrap "$DOMAIN" "$PLIST"
/bin/launchctl kickstart -k "$DOMAIN/com.stillpoint.company"

echo
echo "STILLPOINT 0.4 COMPANY SUPERVISOR ACTIVATED"
echo "Commit: $COMMIT"
echo "LaunchAgent: com.stillpoint.company"
echo "Status: $BIN/status_company_host.sh"
echo "Stop:   $BIN/stop_company_host.sh"
