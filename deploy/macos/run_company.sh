#!/bin/zsh
set -euo pipefail

APP="$HOME/Library/Application Support/StillPoint"
RUNTIME="$APP/Runtime"
RELEASE_ROOT="${STILLPOINT_RELEASE_ROOT:-$APP/current-company}"
VENV="$RELEASE_ROOT/venv"
SERVICE="com.stillpoint.provider.xai-api-key"
ACCOUNT="$(id -un)"

test -x "$VENV/bin/stillpointd" || {
  echo "StillPoint company release is not ready: $RELEASE_ROOT" >&2
  exit 70
}

export STILLPOINT_ROOT="$RUNTIME"
export STILLPOINT_PROVIDER="${STILLPOINT_PROVIDER:-xai}"
export STILLPOINT_MODEL="${STILLPOINT_MODEL:-grok-4.6}"
export STILLPOINT_SMART_ROUTING="${STILLPOINT_SMART_ROUTING:-1}"
export PYTHONDONTWRITEBYTECODE=1

CMD="${1:-serve}"
if [[ "$STILLPOINT_PROVIDER" == "xai" && "$CMD" == "serve" ]]; then
  exec 3< <(/usr/bin/security find-generic-password -a "$ACCOUNT" -s "$SERVICE" -w)
  export STILLPOINT_XAI_API_KEY_FD=3
  unset XAI_API_KEY
fi

exec "$VENV/bin/stillpointd" "$CMD"
