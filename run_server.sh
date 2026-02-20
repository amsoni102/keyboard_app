#!/usr/bin/env bash
# Start the Bluetooth keyboard/mouse server (with sudo for Bluetooth access).
cd "$(dirname "$0")"
exec sudo ./venv/bin/python laptop_server.py
