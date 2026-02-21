# Keyboard & Mouse Remote (Bluetooth)

Control your laptop's keyboard and mouse from your phone over **Bluetooth**. The laptop runs a small Python server; the phone runs a Kivy app (Android).

## Architecture

- **Laptop (server)**: `laptop_server.py` — listens for Bluetooth RFCOMM connections and simulates keyboard/mouse with `pynput`.
- **Phone (client)**: Kivy app in `mobile_app/` — touch pad (move + click), shortcut keys, and scroll. Connects to the laptop via Bluetooth SPP.

## Requirements

### Laptop (Linux)

- Python 3.8+
- Bluetooth hardware
- **PyBluez** and **pynput**

### Python virtual environment (recommended)

One-time setup:

```bash
# Ubuntu/Debian: enable venv and Bluetooth dev headers
sudo apt install python3-venv libbluetooth-dev python3-dev

# Create venv and install dependencies
./setup_venv.sh
```

Then whenever you work on the project:

```bash
source venv/bin/activate
python laptop_server.py
```

To use a different venv folder: `./setup_venv.sh .venv`

### Phone (Android)

- Android device with Bluetooth
- Built APK from the Kivy app (see below), or run the app on desktop with PyBluez for testing

## Quick start

### 1. Run the server on the laptop

```bash
cd /home/pro/Desktop/app_keyboar_mouse_samsung
source venv/bin/activate   # if you use the venv from setup_venv.sh
python laptop_server.py
```

- Make the laptop **discoverable** in Bluetooth settings (for first-time pairing).
- Note the RFCOMM channel printed in the terminal (for reference).

### 2. Pair the laptop from the phone

- On the phone: **Settings → Bluetooth** → turn on Bluetooth → search for the laptop and **pair** (no need to “connect” there; the app will connect).
- Do not skip pairing; the app only lists **paired** devices.

### 3. Run the app on the phone

- **Recommended — Native APK** (for normal use; use this if the Kivy app crashes):

  - **`keyboardmouse.apk`** (project root) — release build for everyday use (~700 KB). Install on the phone and open the app.
  - For testing in browser emulators: **`keyboardmouse-native-debug.apk`** (debug build, larger). Same app; release is smaller and optimized.
  - To rebuild: open `android_app/` in Android Studio and Run, or see `android_app/README.md`.

- **Option A — Kivy APK** (Python/Buildozer):

```bash
cd mobile_app
pip install buildozer
buildozer android debug
```

- APK will be under `mobile_app/bin/`. Install it on the phone and open the app. If it crashes on startup, use the native APK above.

- **Option B — Simulate on desktop** (same UI, no phone): run `./run_desktop.sh` (needs venv + Kivy; BT uses PyBluez).
- **Option C — Android emulator**: create an AVD in Android Studio, then run `./run_emulator.sh` to start emulator, install APK, and launch the app.

- **Option D — Run APK in browser (no install)**: use a web-based Android emulator. **APK to upload:** `keyboardmouse.apk` or `keyboardmouse-native-debug.apk` (in the project root). Open one of these sites, upload the file, and run the app in the browser:
  - **[Appetize.io](https://appetize.io)** — Upload APK, 100 min/month free.
  - **[ApkOnline](https://apkonline.net/)** — Upload and run APK in browser.
  - **[Browserling](https://www.browserling.com/browse/android)** — Free short sessions.
  Bluetooth will not work in the browser; you can still check that the app opens and the UI (device list, touch pad, keys) loads.

- **Option B (legacy) — Test on desktop** (same machine or another PC with Bluetooth):

```bash
cd mobile_app
pip install kivy PyBluez
# Ensure laptop_server.py is running on the target laptop and that it’s paired with this machine
python main.py
```

- In the app: **Refresh** → select the laptop → **Connect**.

## Usage (phone app)

- **Touch pad**: Drag to move the cursor; tap (no drag) for left click.
- **Buttons**: Backspace, Enter, Tab, Esc, Arrow keys.
- **Scroll Up / Scroll Down**: Vertical scroll.

## Protocol (for developers)

Commands are one per line, UTF-8, newline-terminated:

| Command   | Example        | Description        |
|----------|----------------|--------------------|
| `KEY`    | `KEY:a`        | Press and release  |
| `KEY_DOWN` / `KEY_UP` | `KEY_DOWN:shift` | Hold/release key |
| `MOVE`   | `MOVE:10,-5`   | Relative mouse move (dx, dy) |
| `CLICK`  | `CLICK:left`   | Mouse click (left/right/middle) |
| `SCROLL` | `SCROLL:2`     | Vertical scroll    |

The server uses the standard SPP UUID `00001101-0000-1000-8000-00805F9B34FB` so the Android app can connect via RFCOMM.

## Troubleshooting

- **“Do you want to update?” then “App not installed / package appears to be invalid”**: The new APK is signed with a different key than the app already on the phone, so Android blocks the update. **Uninstall the existing Keyboard Mouse app** (Settings → Apps → Keyboard Mouse → Uninstall), then install the new `keyboardmouse.apk` as a fresh install.
- **“Bluetooth not available” on phone**: Ensure the app has Bluetooth permissions (they are in `buildozer.spec`).
- **“SPP service not found” / connection refused**: Start `laptop_server.py` on the laptop and make sure the laptop is paired from the phone.
- **PyBluez install fails (Linux)**: Install `libbluetooth-dev` and `python3-dev`, then `pip install PyBluez` again.
- **No input on laptop / nothing transmitted**: (1) Restart the server with `./run_server.sh` so it has access to your display (script passes `DISPLAY` for pynput). (2) When you use the app, watch the server terminal: you should see `Received: MOVE:...`, `Received: KEY:...` etc. If you see nothing, the phone is not sending or not connected (try Connect again, or re-pair the laptop). (3) If the app says "Connect failed", try again; some phones need a fallback (newer APK has it).
- **“No such file or directory” when starting the server**: BlueZ needs compatibility mode and the Serial Port profile. Do this once:
  1. Edit the Bluetooth service: `sudo nano /lib/systemd/system/bluetooth.service` and change the `ExecStart` line so it ends with `bluetoothd -C` (add ` -C` after `bluetoothd`).
  2. Run: `sudo systemctl daemon-reload && sudo systemctl restart bluetooth`
  3. Register SPP: `sudo sdptool add SP`
  4. Start the server again.

## License

Use and modify as you like.
