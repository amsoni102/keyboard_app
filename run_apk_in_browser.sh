#!/usr/bin/env bash
# Open a web Android emulator and show your APK path so you can upload and run it.
APK="mobile_app/bin/keyboardmouse-0.1-arm64-v8a-debug.apk"
if [ ! -f "$APK" ]; then
  echo "APK not found. Build it first: cd mobile_app && ../venv/bin/buildozer android debug"
  exit 1
fi
echo "APK path (upload this file on the website):"
echo "  $(realpath "$APK")"
echo ""
echo "Opening Appetize.io (upload your APK there to run in browser)..."
xdg-open "https://appetize.io/upload" 2>/dev/null || open "https://appetize.io/upload" 2>/dev/null || echo "Open in browser: https://appetize.io/upload"
