#!/usr/bin/env bash
# Run the mobile app on desktop (simulate) - same UI, same protocol.
# Bluetooth uses PyBluez; pair your phone or use another laptop as server.
set -e
cd "$(dirname "$0")"
if [ ! -d "venv" ]; then
  echo "Create venv first: python3 -m venv venv && source venv/bin/activate && pip install kivy PyBluez"
  exit 1
fi
source venv/bin/activate
# Ensure Kivy is installed for desktop
pip install kivy -q 2>/dev/null || true
export PYTHONPATH="mobile_app:$PYTHONPATH"
cd mobile_app
exec python main.py
