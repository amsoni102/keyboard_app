#!/usr/bin/env bash
# Start the Bluetooth keyboard/mouse server (with sudo for Bluetooth access).
# Preserve DISPLAY so pynput can inject keyboard/mouse into your session.
cd "$(dirname "$0")"
exec sudo -E env DISPLAY="${DISPLAY:-:0}" XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}" ./venv/bin/python laptop_server.py
