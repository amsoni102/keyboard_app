#!/usr/bin/env bash
# One-time setup so laptop_server.py can advertise Bluetooth SPP.
# Run with: sudo ./setup_bluetooth_sdp.sh

set -e
if [[ $EUID -ne 0 ]]; then
   echo "Run with sudo: sudo $0"
   exit 1
fi

BT_SERVICE="/lib/systemd/system/bluetooth.service"
if [[ ! -f "$BT_SERVICE" ]]; then
   BT_SERVICE="/usr/lib/systemd/system/bluetooth.service"
fi
if [[ ! -f "$BT_SERVICE" ]]; then
   echo "bluetooth.service not found."
   exit 1
fi

# Add -C to bluetoothd if not already there
if grep -q 'bluetoothd -C' "$BT_SERVICE"; then
   echo "Compatibility mode (-C) already enabled."
else
   sed -i 's/\(bluetoothd\)$/\1 -C/' "$BT_SERVICE" || \
   sed -i 's/\(bluetoothd\) /\1 -C /' "$BT_SERVICE"
   echo "Added -C to bluetoothd in $BT_SERVICE"
fi

echo "Reloading systemd and restarting Bluetooth..."
systemctl daemon-reload
systemctl restart bluetooth
sleep 1

echo "Registering Serial Port profile (SP)..."
sdptool add SP || true

echo ""
echo "Done. Start the server with:  ./laptop_server.py"
