#!/usr/bin/env bash
bluetoothctl power on 
bluetoothctl discoverable on
exec ./run_server.sh