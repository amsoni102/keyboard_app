"""
Shared protocol for keyboard/mouse control over Bluetooth.
One command per line, UTF-8 encoded. Newline (\n) terminates each command.
"""

# Standard SPP UUID - use this on both laptop server and Android client
SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"

# Commands (client -> server)
CMD_KEY = "KEY"           # KEY:<key> e.g. KEY:a, KEY:enter
CMD_KEY_DOWN = "KEY_DOWN"
CMD_KEY_UP = "KEY_UP"
CMD_MOUSE_MOVE = "MOVE"   # MOVE:dx,dy (relative, integers)
CMD_MOUSE_CLICK = "CLICK" # CLICK:left|right|middle
CMD_SCROLL = "SCROLL"     # SCROLL:dy (vertical, integer)

# Special key names (match pynput Key names where possible)
SPECIAL_KEYS = {
    "enter", "return", "tab", "space", "backspace", "escape", "esc",
    "shift", "ctrl", "control", "alt", "cmd", "command", "win",
    "up", "down", "left", "right", "home", "end", "pageup", "pagedown",
    "insert", "delete", "caps_lock", "num_lock", "scroll_lock",
}

def encode_command(cmd: str, *args: str) -> str:
    """Encode a command for sending (e.g. KEY:a -> 'KEY:a\n')."""
    parts = [cmd] + list(args)
    return ":".join(parts) + "\n"

def parse_command(line: str) -> tuple[str, list[str]] | None:
    """Parse one line into (command, args) or None if invalid."""
    line = line.strip()
    if not line:
        return None
    parts = line.split(":", 1)
    if len(parts) == 1:
        return (parts[0], [])
    return (parts[0].upper(), [parts[1]])
