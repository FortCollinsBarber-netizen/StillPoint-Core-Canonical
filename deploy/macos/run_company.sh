#!/bin/zsh
set -euo pipefail

APP="$HOME/Library/Application Support/StillPoint"
RUNTIME="$APP/Runtime"
VENV="$APP/venv"
SERVICE="com.stillpoint.provider.xai-api-key"
ACCOUNT="$(id -un)"

export STILLPOINT_ROOT="$RUNTIME"
export STILLPOINT_PROVIDER="${STILLPOINT_PROVIDER:-xai}"
export STILLPOINT_MODEL="${STILLPOINT_MODEL:-grok-4.6}"
export STILLPOINT_SMART_ROUTING="${STILLPOINT_SMART_ROUTING:-1}"

CMD="${1:-serve}"
if [[ "$STILLPOINT_PROVIDER" == "xai" && "$CMD" == "serve" ]]; then
  export XAI_API_KEY="$(/usr/bin/security find-generic-password -a "$ACCOUNT" -s "$SERVICE" -w)"
fi

exec "$VENV/bin/stillpointd" "$CMD"
