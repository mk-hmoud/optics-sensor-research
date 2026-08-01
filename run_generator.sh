#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "[*] Creating Virtual Environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "[*] Installing dependencies..."
    pip install -r requirements.txt
else
    echo "[*] Virtual Environment found. Activating..."
    source venv/bin/activate
fi

echo ""
echo "[*] Starting Data Factory..."
python3 src/main.py

echo ""
echo "[*] Factory Run Complete."