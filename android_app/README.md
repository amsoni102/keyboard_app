# Keyboard Mouse (native Android)

Native Kotlin app that uses the same Bluetooth SPP protocol as the Python laptop server. Use this if the Kivy app crashes on your device.

## Build and run

1. Open the `android_app` folder in **Android Studio** (File → Open → select this directory).
2. Wait for Gradle sync.
3. Connect your phone (USB debugging) or start an emulator.
4. Run the app (Run ▶ or Shift+F10).

To build from the command line, install Gradle and run:

```bash
cd android_app
gradle wrapper   # first time only
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

## Permissions

- **Bluetooth**: The app requests `BLUETOOTH_CONNECT` (Android 12+) so it can list paired devices and connect.

## Usage

1. On the laptop, start the server: `./run_server.sh` (or `sudo venv/bin/python laptop_server.py`).
2. Pair the laptop with the phone in system Bluetooth settings if not already paired.
3. Open the app → grant Bluetooth permission → tap **Refresh** → tap a device → **Connect**.
4. Use the touch pad (drag = move, tap = left click), keys, and scroll buttons.

## Protocol

Same as `protocol.py`: one command per line, UTF-8, newline-terminated. SPP UUID `00001101-0000-1000-8000-00805F9B34FB`. Commands: `KEY:…`, `MOVE:dx,dy`, `CLICK:left|right`, `SCROLL:dy`.
