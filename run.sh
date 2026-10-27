#!/usr/bin/env bash
# ========================================================
#       Starting Movie Recommender Application (Unix)
# ========================================================

set -e

# Change to the script's directory
cd "$(dirname "$0")"

# Check if virtual environment exists; create if missing
if [ ! -f "venv/bin/activate" ]; then
    echo "[INFO] Virtual environment not found. Creating venv..."
    python3 -m venv venv
    source venv/bin/activate
    echo "[INFO] Installing dependencies from requirements.txt..."
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt || echo "[WARNING] Some dependencies had warnings during installation."
else
    source venv/bin/activate
fi

# Open the browser in background after 2 seconds
(sleep 2 && {
    if command -v xdg-open > /dev/null; then
        xdg-open "http://localhost:5000"
    elif command -v open > /dev/null; then
        open "http://localhost:5000"
    fi
}) &

# Start the Flask backend server
echo "[INFO] Starting Flask server on http://localhost:5000 ..."
python app.py
