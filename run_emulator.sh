#!/usr/bin/env bash
# Start Android emulator and install the built APK for testing.
# Prerequisite: create an AVD in Android Studio (or run create_avd.sh once).
set -e
cd "$(dirname "$0")"
SDK="${HOME}/.buildozer/android/platform/android-sdk"
EMU="$SDK/emulator/emulator"
ADB="adb"
APK="mobile_app/bin/keyboardmouse-0.1-arm64-v8a-debug.apk"

if [ ! -f "$APK" ]; then
  echo "Build the APK first: cd mobile_app && ../venv/bin/buildozer android debug"
  exit 1
fi

# List AVDs
AVDS=$("$SDK/emulator/emulator" -list-avds 2>/dev/null || true)
if [ -z "$AVDS" ]; then
  echo "No AVD found. Create one:"
  echo "  1. Open Android Studio -> Device Manager -> Create Device"
  echo "  2. Pick a phone (e.g. Pixel 6), download a system image (API 33), finish."
  echo "  3. Or install cmdline-tools and run:"
  echo "     sdkmanager 'system-images;android-33;google_apis;arm64-v8a'"
  echo "     avdmanager create avd -n keyboardmouse -k 'system-images;android-33;google_apis;arm64-v8a' -d pixel_6"
  exit 1
fi

# Use first AVD
AVD_NAME=$(echo "$AVDS" | head -1)
echo "Starting emulator: $AVD_NAME"
"$EMU" -avd "$AVD_NAME" -no-snapshot-load &
EMU_PID=$!
echo "Waiting for emulator to boot (up to 90s)..."
"$ADB" wait-for-device
for i in $(seq 1 90); do
  status=$("$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')
  if [ "$status" = "1" ]; then
    echo "Booted."
    break
  fi
  sleep 1
done

echo "Installing APK..."
"$ADB" install -r "$APK"
echo "Launching app..."
"$ADB" shell am start -n org.example.keyboardmouse/org.kivy.android.PythonActivity
echo "Done. Emulator is running (PID $EMU_PID). Close the emulator window to stop."
