#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export MPLCONFIGDIR="${TMPDIR:-/tmp}/matplotlib"
export YOLO_CONFIG_DIR="${TMPDIR:-/tmp}/Ultralytics"
export PORT="${PORT:-3000}"

# Pick whichever interpreter actually exists. The committed .venv is a POSIX
# virtualenv (.venv/bin/python3); Windows checkouts need .venv/Scripts or the
# system interpreter. Starting with the wrong one is what made the login page
# report "Demo session could not be created" - the server never came up.
if [ -x ".venv/bin/python3" ]; then
    PYTHON=".venv/bin/python3"
elif [ -x ".venv/Scripts/python.exe" ]; then
    PYTHON=".venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
else
    echo "ERROR: no Python interpreter found. Install Python 3.10+ and run:"
    echo "       pip install -r requirements.txt"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "ERROR: .env is missing. Copy .env.example and set SUPABASE_URL and SUPABASE_KEY."
    exit 1
fi

echo "=========================================================="
echo " Starting TARANG Marine Intelligence Platform..."
echo " Interpreter:     $PYTHON"
echo " Web Console URL: http://localhost:${PORT}"
echo " Login Page:      http://localhost:${PORT}/login.html"
echo " System Status:   http://localhost:${PORT}/api/v1/system/status"
echo "=========================================================="

exec "$PYTHON" app.py
