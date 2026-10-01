#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export MPLCONFIGDIR=/tmp/matplotlib
export YOLO_CONFIG_DIR=/tmp/Ultralytics
export PORT="${PORT:-3000}"

echo "=========================================================="
echo " Starting TARANG Marine Intelligence Platform..."
echo " Web Console URL: http://localhost:${PORT}"
echo " Login Page:      http://localhost:${PORT}/login.html"
echo "=========================================================="

exec .venv/bin/python3 app.py
