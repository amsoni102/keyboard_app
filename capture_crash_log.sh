#!/usr/bin/env bash
# Capture crash log when the app fails after "Loading...".
# Run this while the emulator (or device) is connected, then launch the app and let it crash.
# The last lines will show the Python/Kivy/native crash.
set -e
echo "Make sure the emulator is running or phone is connected with USB debugging."
echo "Launch the Keyboard Mouse app and let it crash. Press Ctrl+C when done."
echo "Saving log to crash_log.txt ..."
adb logcat -c
adb logcat 2>&1 | tee crash_log.txt | grep -E "python|kivy|Python|FATAL|AndroidRuntime|Exception|Error|keyboardmouse" --line-buffered
