#!/bin/bash

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BOOTSTRAP="$ROOT/roughcut/scripts/bootstrap_launch.py"

if [[ ! -f "$BOOTSTRAP" ]]; then
  echo "[ERROR] RoughCut bootstrap script was not found at:"
  echo "[ERROR]   $BOOTSTRAP"
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
else
  echo "[ERROR] Python 3.10+ is required before RoughCut can bootstrap itself."
  exit 1
fi

cd "$ROOT"
echo "[INFO] Running RoughCut prelaunch bootstrap..."
"$PYTHON_CMD" "$BOOTSTRAP" --mode standalone
