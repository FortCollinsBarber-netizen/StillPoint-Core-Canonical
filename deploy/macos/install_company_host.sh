#!/bin/bash
set -euo pipefail

REPO="FortCollinsBarber-netizen/StillPoint-Core-Canonical"
APP="$HOME/Library/Application Support/StillPoint"
RELEASES="$APP/releases"
CURRENT="$APP/current-company"
RUNTIME="$APP/Runtime"
BIN="$APP/bin"
LOGDIR="$HOME/Library/Logs/StillPoint"
PLIST="$HOME/Library/LaunchAgents/com.stillpoint.company.plist"
XAI_SERVICE="com.stillpoint.provider.xai-api-key"
ACCOUNT="$(id -un)"
PYTHON_BIN="${STILLPOINT_PYTHON:-/opt/homebrew/opt/python@3.13/libexec/bin/python3}"

die(){ echo "ERROR: $*" >&2; exit 1; }

for cmd in git gh security; do command -v "$cmd" >/dev/null || die "$cmd is required"; done
test -x "$PYTHON_BIN" || die "Python 3.13 not found at $PYTHON_BIN"

mkdir -p "$APP" "$RELEASES" "$RUNTIME/state" "$BIN" "$LOGDIR" "$HOME/Library/LaunchAgents"

COMMIT="$(gh api "repos/$REPO/commits/main" --jq '.sha')"
test -n "$COMMIT" || die "could not resolve canonical main commit"
echo "Canonical commit: $COMMIT"

echo "==> Verify canonical push CI"
RUN_JSON="$(gh run list --repo "$REPO" --commit "$COMMIT" --workflow "StillPoint Core CI" --event push --limit 5 --json databaseId,status,conclusion,headSha --jq '.[0]')"
test -n "$RUN_JSON" && test "$RUN_JSON" != "null" || die "no push CI found for canonical commit"
CI_STATUS="$(printf '%s' "$RUN_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
CI_CONCLUSION="$(printf '%s' "$RUN_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["conclusion"])')"
test "$CI_STATUS" = "completed" && test "$CI_CONCLUSION" = "success" || die "canonical CI is not green"

RELEASE="$RELEASES/$COMMIT"
CORE="$RELEASE/core"
VENV="$RELEASE/venv"

if [ -f "$RELEASE/.ready" ]; then
  test -d "$CORE/.git" || die "release marker exists without source checkout: $RELEASE"
  test "$(git -C "$CORE" rev-parse HEAD)" = "$COMMIT" || die "release commit mismatch"
  test -x "$VENV/bin/stillpointd" || die "release marker exists without company runtime"
  echo "==> Reuse verified immutable release $COMMIT"
else
  test ! -e "$RELEASE" || die "incomplete release exists; refusing to mutate it: $RELEASE"
  echo "==> Build new commit-addressed release"
  mkdir -p "$RELEASE"
  git clone "https://github.com/$REPO.git" "$CORE"
  git -C "$CORE" checkout --detach "$COMMIT"
  test "$(git -C "$CORE" rev-parse HEAD)" = "$COMMIT" || die "release checkout mismatch"
  "$PYTHON_BIN" -m venv "$VENV"
  "$VENV/bin/python" -m pip install --upgrade pip
  "$VENV/bin/python" -m pip install "$CORE"
  touch "$RELEASE/.ready"
  chmod -R a-w "$RELEASE"
fi

VERSION="$("$PYTHON_BIN" - "$CORE" <<'PY'
import re,sys
from pathlib import Path
text=(Path(sys.argv[1])/"pyproject.toml").read_text()
print(re.search(r'^version\s*=\s*"([^"]+)"',text,re.M).group(1))
PY
)"
echo "Release version: $VERSION"

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

echo "==> Candidate release structural preflight"
STILLPOINT_RELEASE_ROOT="$RELEASE" "$BIN/run_company.sh" check

echo "==> Live xAI credential/model capability preflight"
/usr/bin/security find-generic-password -a "$ACCOUNT" -s "$XAI_SERVICE" -w \
  | "$VENV/bin/python" "$CORE/deploy/macos/probe_xai_access.py" --model "grok-4.6" \
  || die "xAI credential/model capability preflight failed"

echo "==> Atomically select release for Company"
"$PYTHON_BIN" - "$RELEASE" "$CURRENT" <<'PY'
import os,sys
target,current=sys.argv[1],sys.argv[2]
tmp=f"{current}.tmp.{os.getpid()}"
try:
    os.unlink(tmp)
except FileNotFoundError:
    pass
os.symlink(target,tmp)
os.replace(tmp,current)
PY

echo "==> Activate StillPoint company supervisor"
DOMAIN="gui/$(id -u)"
/bin/launchctl bootout "$DOMAIN" "$PLIST" 2>/dev/null || true
/bin/launchctl bootstrap "$DOMAIN" "$PLIST"
/bin/launchctl kickstart -k "$DOMAIN/com.stillpoint.company"

echo
echo "STILLPOINT COMPANY SUPERVISOR ACTIVATED"
echo "Commit: $COMMIT"
echo "Version: $VERSION"
echo "Release: $RELEASE"
echo "LaunchAgent: com.stillpoint.company"
echo "Status: $BIN/status_company_host.sh"
echo "Stop:   $BIN/stop_company_host.sh"
