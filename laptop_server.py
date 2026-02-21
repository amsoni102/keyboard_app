#!/usr/bin/env python3
"""
Bluetooth keyboard/mouse server. Run in two parts so pynput runs as your user
(no sudo) and actually controls the cursor/keys:

  Terminal 1:  ./venv/bin/python laptop_server.py --user
  Terminal 2:   sudo ./venv/bin/python laptop_server.py --bt

Or use  ./run_server.sh  to start both.
"""

import os
import pwd
import socket
import subprocess
import sys
import logging

from protocol import SPP_UUID, parse_command, CMD_KEY, CMD_KEY_DOWN, CMD_KEY_UP
from protocol import CMD_MOUSE_MOVE, CMD_MOUSE_CLICK, CMD_SCROLL

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# xdotool key names (X11) for reliable injection into the display
XDOTOOL_KEYS = {
    "enter": "Return", "return": "Return", "tab": "Tab", "space": "space",
    "backspace": "BackSpace", "escape": "Escape", "esc": "Escape",
    "up": "Up", "down": "Down", "left": "Left", "right": "Right",
    "home": "Home", "end": "End", "pageup": "Page_Up", "pagedown": "Page_Down",
    "insert": "Insert", "delete": "Delete",
}

# ydotool: Linux evdev keycodes (for Wayland). Format keycode:1 keycode:0 for press+release.
# From input-event-codes.h: ESC=1, TAB=15, ENTER=28, BACKSPACE=14, SPACE=57, etc.
YDOTOOL_KEYCODES = {
    "enter": 28, "return": 28, "tab": 15, "space": 57,
    "backspace": 14, "escape": 1, "esc": 1,
    "up": 103, "down": 108, "left": 105, "right": 106,
    "home": 102, "end": 107, "pageup": 104, "pagedown": 109,
    "insert": 110, "delete": 111,
}


def _ydotool_available():
    """True if ydotool is installed and ydotoold is running (for Wayland)."""
    if os.name != "posix":
        return False
    try:
        r = subprocess.run(
            ["ydotool", "mousemove", "0", "0"],
            capture_output=True,
            timeout=5,
            env=os.environ,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _ydotool_run(*args):
    """Run ydotool; return True on success."""
    try:
        r = subprocess.run(
            ["ydotool"] + list(args),
            env=os.environ,
            capture_output=True,
            timeout=2,
        )
        return r.returncode == 0
    except Exception:
        return False


def _handle_command_ydotool(cmd: str, args: list[str]) -> bool:
    """Inject key/mouse via ydotool (Wayland and X11)."""
    try:
        if cmd == CMD_KEY:
            if not args:
                return True
            name = args[0].strip().lower()
            code = YDOTOOL_KEYCODES.get(name)
            if code is None:
                if len(name) == 1:
                    # Use 'type' for single chars
                    _ydotool_run("type", name)
                return True
            _ydotool_run("key", f"{code}:1", f"{code}:0")
        elif cmd == CMD_KEY_DOWN:
            if not args:
                return True
            code = YDOTOOL_KEYCODES.get(args[0].strip().lower())
            if code is not None:
                _ydotool_run("key", f"{code}:1")
        elif cmd == CMD_KEY_UP:
            if not args:
                return True
            code = YDOTOOL_KEYCODES.get(args[0].strip().lower())
            if code is not None:
                _ydotool_run("key", f"{code}:0")
        elif cmd == CMD_MOUSE_MOVE:
            if not args or "," not in args[0]:
                return True
            dx, dy = args[0].strip().split(",", 1)
            dx, dy = int(dx.strip()), int(dy.strip())
            _ydotool_run("mousemove", str(dx), str(dy))
        elif cmd == CMD_MOUSE_CLICK:
            btn = (args or ["left"])[0].strip().lower()
            # ydotool click: 0x00=left, 0x01=right, 0x02=middle
            code = "0x00" if btn == "left" else ("0x01" if btn == "right" else "0x02")
            _ydotool_run("click", code)
        elif cmd == CMD_SCROLL:
            if not args:
                return True
            dy = int(args[0].strip())
            # Scroll: 0x04=scroll up, 0x05=scroll down (ydotool click)
            code = "0x04" if dy > 0 else "0x05"
            count = min(max(abs(dy), 1), 20)
            for _ in range(count):
                _ydotool_run("click", code)
        else:
            log.warning("Unknown command: %s", cmd)
    except Exception as e:
        log.exception("ydotool command failed: %s %s", cmd, args)
    return True


def _xdotool_available():
    """True if xdotool is installed and we can use it to control the display."""
    if os.name != "posix":
        return False
    env = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")}
    try:
        r = subprocess.run(
            ["xdotool", "version"],
            capture_output=True,
            timeout=2,
            env=env,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# Log xdotool errors only occasionally to avoid spam
_xdotool_error_logged = False

def _xdotool_run(env, *args):
    """Run xdotool; on failure log stderr once so we see why injection fails."""
    global _xdotool_error_logged
    try:
        r = subprocess.run(
            ["xdotool"] + list(args),
            env=env,
            capture_output=True,
            timeout=2,
        )
        if r.returncode != 0 and not _xdotool_error_logged:
            _xdotool_error_logged = True
            err = (r.stderr or b"").decode("utf-8", errors="replace").strip()
            log.error("xdotool failed (return %s). Stderr: %s", r.returncode, err or "(none)")
            log.error("DISPLAY=%s - if empty or wrong, input will not control the screen.", env.get("DISPLAY", ""))
        return r.returncode == 0
    except Exception as e:
        if not _xdotool_error_logged:
            _xdotool_error_logged = True
            log.exception("xdotool run failed: %s", e)
        return False


def _handle_command_xdotool(cmd: str, args: list[str]) -> bool:
    """Inject key/mouse via xdotool so they actually control the screen (X11)."""
    env = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")}
    try:
        if cmd == CMD_KEY:
            if not args:
                return True
            name = args[0].strip().lower()
            key = XDOTOOL_KEYS.get(name, name if len(name) == 1 else None)
            if key is None:
                return True
            _xdotool_run(env, "key", key)
        elif cmd == CMD_KEY_DOWN:
            if not args:
                return True
            name = args[0].strip().lower()
            key = XDOTOOL_KEYS.get(name, name if len(name) == 1 else None)
            if key:
                _xdotool_run(env, "keydown", key)
        elif cmd == CMD_KEY_UP:
            if not args:
                return True
            name = args[0].strip().lower()
            key = XDOTOOL_KEYS.get(name, name if len(name) == 1 else None)
            if key:
                _xdotool_run(env, "keyup", key)
        elif cmd == CMD_MOUSE_MOVE:
            if not args or "," not in args[0]:
                return True
            dx, dy = args[0].strip().split(",", 1)
            dx, dy = int(dx.strip()), int(dy.strip())
            _xdotool_run(env, "mousemove_relative", "--", str(dx), str(dy))
        elif cmd == CMD_MOUSE_CLICK:
            btn = (args or ["left"])[0].strip().lower()
            button = "1" if btn != "right" and btn != "middle" else ("3" if btn == "right" else "2")
            _xdotool_run(env, "click", button)
        elif cmd == CMD_SCROLL:
            if not args:
                return True
            dy = int(args[0].strip())
            count = min(max(abs(dy), 1), 20)
            for _ in range(count):
                _xdotool_run(env, "click", "4" if dy > 0 else "5")
        else:
            log.warning("Unknown command: %s", cmd)
    except Exception as e:
        log.exception("xdotool command failed: %s %s", cmd, args)
    return True

def _pyautogui_available():
    """True if pyautogui can be imported and used (works on some X11/Wayland setups)."""
    try:
        import pyautogui
        pyautogui.size()
        return True
    except Exception:
        return False


# PyAutoGUI key names (for press())
PYAUTOGUI_KEYS = {
    "enter": "enter", "return": "enter", "tab": "tab", "space": "space",
    "backspace": "backspace", "escape": "escape", "esc": "escape",
    "up": "up", "down": "down", "left": "left", "right": "right",
    "home": "home", "end": "end", "pageup": "pageup", "pagedown": "pagedown",
    "insert": "insert", "delete": "delete",
}


def _handle_command_pyautogui(cmd: str, args: list[str]) -> bool:
    """Inject key/mouse via pyautogui (often works where xdotool/ydotool fail)."""
    try:
        import pyautogui
        pyautogui.FAILSAFE = False  # allow remote control without corner trigger
        if cmd == CMD_KEY:
            if not args:
                return True
            name = args[0].strip().lower()
            key = PYAUTOGUI_KEYS.get(name)
            if key:
                pyautogui.press(key)
            elif len(name) == 1:
                pyautogui.write(name)
        elif cmd == CMD_KEY_DOWN:
            if not args:
                return True
            key = PYAUTOGUI_KEYS.get(args[0].strip().lower())
            if key:
                pyautogui.keyDown(key)
        elif cmd == CMD_KEY_UP:
            if not args:
                return True
            key = PYAUTOGUI_KEYS.get(args[0].strip().lower())
            if key:
                pyautogui.keyUp(key)
        elif cmd == CMD_MOUSE_MOVE:
            if not args or "," not in args[0]:
                return True
            dx, dy = args[0].strip().split(",", 1)
            dx, dy = int(dx.strip()), int(dy.strip())
            pyautogui.moveRel(dx, -dy, duration=0)
        elif cmd == CMD_MOUSE_CLICK:
            btn = (args or ["left"])[0].strip().lower()
            if btn == "right":
                pyautogui.click(button="right")
            elif btn == "middle":
                pyautogui.click(button="middle")
            else:
                pyautogui.click(button="left")
        elif cmd == CMD_SCROLL:
            if not args:
                return True
            dy = int(args[0].strip())
            pyautogui.scroll(dy)
        else:
            log.warning("Unknown command: %s", cmd)
    except Exception as e:
        log.exception("pyautogui command failed: %s %s", cmd, args)
    return True


# Unix socket in the user's home so the user can always unlink it (no root-owned /tmp file)
def _socket_path(uid=None):
    if uid is None:
        uid = os.getuid()
    return os.path.join(pwd.getpwuid(int(uid)).pw_dir, ".keyboardmouse.sock")


def _init_pynput():
    """Import and create pynput controllers (only in --user mode)."""
    try:
        from pynput import keyboard, mouse
        from pynput.keyboard import Key
    except ImportError:
        print("pynput not found. Install: pip install pynput")
        sys.exit(1)
    return keyboard.Controller(), mouse.Controller(), Key


def _handle_command(keyboard_controller, mouse_controller, Key, cmd: str, args: list[str]) -> bool:
    """Execute one command. Returns False to stop processing."""
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

    def key_from_string(name: str):
        n = name.strip().lower()
        if n in KEY_MAP:
            return KEY_MAP[n]
        if len(n) == 1:
            return n
        return name

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


def _print_input_diagnostic():
    """Print why input might not control the screen, so the user can fix it."""
    session = os.environ.get("XDG_SESSION_TYPE", "?")
    print()
    print("--- Input backend diagnostic ---")
    print("  XDG_SESSION_TYPE =", session)
    # xdotool
    try:
        r = subprocess.run(
            ["xdotool", "getmouselocation"],
            env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")},
            capture_output=True, timeout=2,
        )
        print("  xdotool: installed, getmouselocation return code =", r.returncode)
        if r.returncode != 0 and r.stderr:
            print("    stderr:", r.stderr.decode("utf-8", errors="replace")[:200])
    except FileNotFoundError:
        print("  xdotool: NOT INSTALLED (sudo apt install xdotool)")
    except Exception as e:
        print("  xdotool:", e)
    # ydotool (check with mousemove 0 0 - some builds don't have 'help')
    try:
        r = subprocess.run(["ydotool", "mousemove", "0", "0"], capture_output=True, timeout=2)
        ok = r.returncode == 0
        print("  ydotool: installed, daemon reachable =", ok)
        if not ok and r.stderr:
            print("    stderr:", r.stderr.decode("utf-8", errors="replace")[:150])
    except FileNotFoundError:
        print("  ydotool: NOT INSTALLED (build from github.com/ReimuNotMoe/ydotool)")
    except Exception as e:
        print("  ydotool:", e)
    # ydotoold running?
    try:
        r = subprocess.run(["pgrep", "-x", "ydotoold"], capture_output=True, timeout=1)
        print("  ydotoold daemon running:", r.returncode == 0)
    except Exception:
        print("  ydotoold: check manually (pgrep ydotoold)")
    # pyautogui
    try:
        import pyautogui
        pyautogui.size()
        print("  pyautogui: available")
    except Exception:
        print("  pyautogui: not available (pip install pyautogui)")
    print()
    if session == "wayland":
        print(">>> RECOMMENDED: On Wayland, xdotool does NOT control the visible desktop.")
        print(">>> To get real control: LOG OUT → at login choose 'Ubuntu on Xorg' → LOG IN")
        print(">>> Then:  sudo apt install xdotool   and run  ./run_server.sh")
        print(">>> (X11 + xdotool is the reliable way on Ubuntu.)")
    print("---")


def run_user_server():
    """Run as your user: listen on Unix socket, inject input via ydotool (Wayland), xdotool (X11), or pynput."""
    _print_input_diagnostic()

    session = os.environ.get("XDG_SESSION_TYPE", "")
    forced = os.environ.get("BACKEND", "").strip().lower()
    use_ydotool = _ydotool_available() or os.environ.get("USE_YDOTOOL", "")
    use_xdotool = _xdotool_available() or os.environ.get("USE_XDOTOOL", "")
    handle = None

    def try_pyautogui():
        if _pyautogui_available():
            print(">>> Input backend: pyautogui (commands will control the screen)")
            log.info("Using pyautogui to control keyboard/mouse")
            return lambda c, a: _handle_command_pyautogui(c, a)
        return None

    def try_xdotool():
        env = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")}
        r = subprocess.run(["xdotool", "getmouselocation"], env=env, capture_output=True, timeout=2)
        if r.returncode == 0:
            print(">>> Input backend: xdotool (commands will control the screen)")
            log.info("Using xdotool to control keyboard/mouse")
            return lambda c, a: _handle_command_xdotool(c, a)
        return None

    def try_ydotool():
        if _ydotool_available():
            print(">>> Input backend: ydotool (commands will control the screen)")
            log.info("Using ydotool to control keyboard/mouse")
            return lambda c, a: _handle_command_ydotool(c, a)
        return None

    # Forced backend
    if forced == "pyautogui":
        handle = try_pyautogui()
        if handle is None:
            print(">>> BACKEND=pyautogui but pyautogui failed. Install: pip install pyautogui")
            kbd, mouse_ctrl, Key = _init_pynput()
            handle = lambda c, a: _handle_command(kbd, mouse_ctrl, Key, c, a)
    elif forced == "xdotool":
        handle = try_xdotool()
        if handle is None:
            print(">>> BACKEND=xdotool but xdotool failed. Install: sudo apt install xdotool (and use an X11 session for best results)")
            kbd, mouse_ctrl, Key = _init_pynput()
            handle = lambda c, a: _handle_command(kbd, mouse_ctrl, Key, c, a)
    elif forced == "ydotool":
        handle = try_ydotool()
        if handle is None:
            print(">>> BACKEND=ydotool failed: ydotool not installed or ydotoold not running.")
            print(">>> Option A: Install ydotool (build from source): github.com/ReimuNotMoe/ydotool")
            print(">>>           Then run:  ydotoold &   and restart this server.")
            print(">>> Option B (easier): Use X11 + xdotool instead:")
            print(">>>           Log out → at login choose 'Ubuntu on Xorg' → log in")
            print(">>>           Then:  sudo apt install xdotool   and run  ./run_server.sh  (no BACKEND=)")
            kbd, mouse_ctrl, Key = _init_pynput()
            handle = lambda c, a: _handle_command(kbd, mouse_ctrl, Key, c, a)
    # Auto: try pyautogui first (works on many setups), then xdotool (X11), then ydotool (Wayland)
    else:
        handle = try_pyautogui()
        if handle is None:
            handle = try_xdotool()
        if handle is None and session == "wayland":
            handle = try_ydotool()
        if handle is None:
            print(">>> Input backend: pynput (commands may only appear in terminal)")
            print(">>> Install one of:  pip install pyautogui   or   sudo apt install xdotool   (and use X11)")
            kbd, mouse_ctrl, Key = _init_pynput()
            handle = lambda c, a: _handle_command(kbd, mouse_ctrl, Key, c, a)

    path = _socket_path()
    if os.path.exists(path):
        try:
            os.unlink(path)
        except PermissionError:
            log.error("Cannot remove %s (owned by root?). Remove it: sudo rm %s", path, path)
            sys.exit(1)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(path)
    sock.listen(1)
    try:
        os.chmod(path, 0o777)
    except OSError:
        pass
    log.info("User server listening on %s", path)

    while True:
        try:
            conn, _ = sock.accept()
            log.info("Relay connected")
            buffer = b""
            try:
                while True:
                    data = conn.recv(4096)
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
                        if parsed and not handle(parsed[0], parsed[1]):
                            break
            except (OSError, ConnectionResetError) as e:
                log.info("Relay disconnected: %s", e)
            finally:
                conn.close()
        except KeyboardInterrupt:
            break
        except Exception as e:
            log.exception("Error: %s", e)

    sock.close()
    if os.path.exists(path):
        os.unlink(path)
    log.info("User server stopped.")


def run_bt_relay():
    """Run as root (sudo): bind Bluetooth, forward bytes to user's Unix socket."""
    try:
        import bluetooth
        from bluetooth.btcommon import BluetoothError
    except ImportError:
        print("PyBluez is required. Install: pip install PyBluez")
        print("On Ubuntu/Debian: sudo apt install libbluetooth-dev python3-dev")
        sys.exit(1)

    path = _socket_path(os.environ.get("SUDO_UID", os.getuid()))
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("", 1))
    server_sock.listen(1)

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
        if "no advertisable device" in errmsg or "advertisable" in errmsg:
            print("  Turn Bluetooth ON and make this PC discoverable:")
            print("    • Settings → Bluetooth → turn ON, then set this device to visible/discoverable")
            print("  Or from terminal:  bluetoothctl power on && bluetoothctl discoverable on")
            print()
        elif "permission denied" in errmsg or "errno 13" in errmsg:
            print("  Run with sudo:  sudo ./venv/bin/python laptop_server.py --bt")
        elif "no such file or directory" in errmsg or "errno 2" in errmsg:
            print("  BlueZ SDP may need: sudo sdptool add SP  and bluetoothd -C")
        print()
        sys.exit(1)

    log.info("Bluetooth relay listening on RFCOMM channel 1. Connect from the phone.")

    while True:
        try:
            client_sock, client_info = server_sock.accept()
            log.info("Connected from %s", client_info)
            if not os.path.exists(path):
                log.error("User server socket %s not found. Start it first: python laptop_server.py --user", path)
                client_sock.close()
                continue
            try:
                relay = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                relay.connect(path)
                try:
                    while True:
                        data = client_sock.recv(4096)
                        if not data:
                            break
                        relay.sendall(data)
                finally:
                    relay.close()
            except (OSError, ConnectionResetError) as e:
                log.info("Relay or client closed: %s", e)
            finally:
                client_sock.close()
        except KeyboardInterrupt:
            break
        except Exception as e:
            log.exception("Error: %s", e)

    server_sock.close()
    log.info("Bluetooth relay stopped.")


if __name__ == "__main__":
    if "--user" in sys.argv:
        run_user_server()
    elif "--bt" in sys.argv:
        run_bt_relay()
    else:
        print("Usage:")
        print("  Terminal 1:  ./venv/bin/python laptop_server.py --user")
        print("  Terminal 2:  sudo ./venv/bin/python laptop_server.py --bt")
        print("Or run  ./run_server.sh  to start both.")
        sys.exit(0)
