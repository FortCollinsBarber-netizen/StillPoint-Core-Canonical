#!/bin/bash
set -euo pipefail

APP_SUPPORT="$HOME/Library/Application Support/StillPoint"
RUNTIME="$APP_SUPPORT/Runtime"
RELEASE_ROOT="${STILLPOINT_RELEASE_ROOT:-$APP_SUPPORT/current-signal}"
VENV="$RELEASE_ROOT/venv"

ICLOUD_SERVICE="com.stillpoint.signal.icloud-app-password"
XAI_SERVICE="com.stillpoint.signal.xai-api-key"
ACCOUNT="$(id -un)"

test -x "$VENV/bin/stillpoint-signal-mail" || {
  echo "StillPoint Signal release is not ready: $RELEASE_ROOT" >&2
  exit 70
}

exec 3< <(/usr/bin/security find-generic-password -a "$ACCOUNT" -s "$ICLOUD_SERVICE" -w)
exec 4< <(/usr/bin/security find-generic-password -a "$ACCOUNT" -s "$XAI_SERVICE" -w)

export STILLPOINT_ROOT="$RUNTIME"
export STILLPOINT_MAIL_PROVIDER="icloud"
export STILLPOINT_MAIL_ACCOUNT="fortcollinsbarber@icloud.com"
export STILLPOINT_MAIL_JURISDICTION="personal_business"
export STILLPOINT_SIGNAL_DELEGATION_ID="signal-delegation-icloud-personal-business-v1"
export STILLPOINT_SIGNAL_MAIL_TRIGGER_ID="signal-trigger-icloud-personal-business-v1"
export STILLPOINT_SIGNAL_GOVERNANCE_SHA256="abbada7549a95510d9552441a4f7bb1c92977f899cdfa953e8e394b058d00cc9"
export STILLPOINT_SIGNAL_FACTS_FILE="$RUNTIME/state/signal_icloud_personal_business.facts.json"
export STILLPOINT_PROVIDER="xai"
export STILLPOINT_SIGNAL_MODEL="${STILLPOINT_SIGNAL_MODEL:-grok-4.6}"
export STILLPOINT_ICLOUD_APP_PASSWORD_FD=3
export STILLPOINT_XAI_API_KEY_FD=4
unset STILLPOINT_ICLOUD_APP_PASSWORD XAI_API_KEY
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1


CMD="${1:-serve}"
case "$CMD" in
  check|once|serve) ;;
  *) echo "usage: $0 [check|once|serve]" >&2; exit 64 ;;
esac

exec "$VENV/bin/stillpoint-signal-mail" "$CMD"
