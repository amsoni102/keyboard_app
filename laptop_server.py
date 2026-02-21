#!/usr/bin/env python3
"""
Bluetooth server that runs on the laptop. Listens for connections from the
mobile app and controls keyboard and mouse using pynput.
"""

import socket
import sys
import logging

try:
    from pynput import keyboard, mouse
    from pynput.keyboard import Key
except ImportError:
    print("pynput not found. When using sudo, run with the venv Python:")
    print("  sudo venv/bin/python laptop_server.py")
    print("Or use the helper script:  ./run_server.sh")
    sys.exit(1)

try:
    import bluetooth
    from bluetooth.btcommon import BluetoothError
except ImportError:
    print("PyBluez is required on the laptop. Install: pip install PyBluez")
    print("On Ubuntu/Debian you may need: sudo apt install libbluetooth-dev python3-dev")
    sys.exit(1)

from protocol import SPP_UUID, parse_command, CMD_KEY, CMD_KEY_DOWN, CMD_KEY_UP
from protocol import CMD_MOUSE_MOVE, CMD_MOUSE_CLICK, CMD_SCROLL, SPECIAL_KEYS

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Controllers (global so command handler can use them)
keyboard_controller = keyboard.Controller()
mouse_controller = mouse.Controller()

# Map string key names to pynput Key enum
KEY_MAP = {
    "enter": Key.enter, "return": Key.enter,
    "tab": Key.tab, "space": Key.space, "backspace": Key.backspace,
    "escape": Key.esc, "esc": Key.esc,
    "shift": Key.shift, "ctrl": Key.ctrl, "control": Key.ctrl,
    "alt": Key.alt, "cmd": Key.cmd, "command": Key.cmd, "win": Key.cmd,
    "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
    "home": Key.home, "end": Key.end,
    "pageup": Key.page_up, "pagedown": Key.page_down,
    "insert": Key.insert, "delete": Key.delete,
    "caps_lock": Key.caps_lock, "num_lock": Key.num_lock,
    "scroll_lock": Key.scroll_lock,
}


def key_from_string(name: str) -> Key | str:
    """Return pynput Key or single char for the given key name."""
    n = name.strip().lower()
    if n in KEY_MAP:
        return KEY_MAP[n]
    if len(n) == 1:
        return n
    return name  # fallback, pynput may reject


def handle_command(cmd: str, args: list[str]) -> bool:
    """Execute one command. Returns False to stop processing."""
    try:
        if cmd == CMD_KEY:
            if not args:
                return True
            k = key_from_string(args[0])
            keyboard_controller.press(k)
            keyboard_controller.release(k)
        elif cmd == CMD_KEY_DOWN:
            if not args:
                return True
            keyboard_controller.press(key_from_string(args[0]))
        elif cmd == CMD_KEY_UP:
            if not args:
                return True
            keyboard_controller.release(key_from_string(args[0]))
        elif cmd == CMD_MOUSE_MOVE:
            if not args:
                return True
            part = args[0]
            if "," in part:
                dx, dy = part.split(",", 1)
                dx, dy = int(dx.strip()), int(dy.strip())
                mouse_controller.move(dx, dy)
        elif cmd == CMD_MOUSE_CLICK:
            btn = (args or ["left"])[0].strip().lower()
            button = mouse.Button.left
            if btn == "right":
                button = mouse.Button.right
            elif btn == "middle":
                button = mouse.Button.middle
            mouse_controller.click(button)
        elif cmd == CMD_SCROLL:
            if not args:
                return True
            dy = int(args[0].strip())
            mouse_controller.scroll(0, dy)
        else:
            log.warning("Unknown command: %s", cmd)
    except Exception as e:
        log.exception("Command failed: %s %s", cmd, args)
    return True


def run_server(port: int | None = None):
    # Use channel 1 so Android fallback (createRfcommSocket(1)) can connect if SDP fails
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("", port if port is not None else 1))
    server_sock.listen(1)

    channel = server_sock.getsockname()[1]
    try:
        bluetooth.advertise_service(
            server_sock,
            "KeyboardMouse",
            service_id=SPP_UUID,
            service_classes=[SPP_UUID, bluetooth.SERIAL_PORT_CLASS],
            profiles=[bluetooth.SERIAL_PORT_PROFILE],
        )
    except BluetoothError as e:
        server_sock.close()
        log.error("Bluetooth error: %s", e)
        errmsg = str(e).lower()
        print()
        if "no such file or directory" in errmsg or "errno 2" in errmsg:
            print("  BlueZ SDP is not available. Do the following (one-time fix):")
            print()
            print("  1. Enable compatibility mode: add -C to bluetoothd in the service file.")
            print("     sudo nano /lib/systemd/system/bluetooth.service")
            print("     Change the ExecStart line to end with:  bluetoothd -C")
            print()
            print("  2. Reload and restart Bluetooth:")
            print("     sudo systemctl daemon-reload")
            print("     sudo systemctl restart bluetooth")
            print()
            print("  3. Register the Serial Port profile:")
            print("     sudo sdptool add SP")
            print()
            print("  4. Run this server again.")
        elif "permission denied" in errmsg or "errno 13" in errmsg:
            print("  Run the server with sudo:  sudo ./laptop_server.py")
            print("  (Or: sudo venv/bin/python laptop_server.py)")
        elif "no advertisable device" in errmsg:
            print("  Turn Bluetooth ON in system settings (or: bluetoothctl power on)")
            print("  Make this PC discoverable in Settings → Bluetooth.")
        else:
            print("  Ensure Bluetooth is ON and discoverable.")
            print("  If you see 'Permission denied', run with: sudo ./laptop_server.py")
        print()
        sys.exit(1)

    log.info("Bluetooth server listening on RFCOMM channel %s. Make this device discoverable and pair from your phone.", channel)

    while True:
        try:
            client_sock, client_info = server_sock.accept()
            log.info("Connected from %s", client_info)
            buffer = b""
            try:
                while True:
                    data = client_sock.recv(4096)
                    if not data:
                        break
                    buffer += data
                    while b"\n" in buffer or b"\r" in buffer:
                        for sep in (b"\n", b"\r"):
                            if sep in buffer:
                                line, buffer = buffer.split(sep, 1)
                                break
                        else:
                            break
                        try:
                            line_str = line.decode("utf-8").strip()
                        except UnicodeDecodeError:
                            continue
                        if not line_str:
                            continue
                        log.info("Received: %s", line_str)
                        parsed = parse_command(line_str)
                        if parsed and not handle_command(parsed[0], parsed[1]):
                            break
            except (OSError, ConnectionResetError) as e:
                log.info("Client disconnected: %s", e)
            finally:
                client_sock.close()
        except KeyboardInterrupt:
            break
        except Exception as e:
            log.exception("Error: %s", e)

    server_sock.close()
    log.info("Server stopped.")


if __name__ == "__main__":
    run_server()
