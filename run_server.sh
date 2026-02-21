#!/usr/bin/env bash
# Start both parts: user process (pynput, no sudo) and Bluetooth relay (sudo).
# This way the keyboard/mouse are controlled by your user session.
cd "$(dirname "$0")"

USER_PID=
cleanup() {
  if [ -n "$USER_PID" ]; then
    kill "$USER_PID" 2>/dev/null
  fi
  exit 0
}
trap cleanup INT TERM

# So the user process can control the display (xdotool/pynput need this)
export DISPLAY="${DISPLAY:-:0}"

# Force backend: BACKEND=pyautogui | xdotool | ydotool
# Example:  BACKEND=pyautogui ./run_server.sh   (pyautogui often works where xdotool does not)
export BACKEND="${BACKEND:-}"

# Start ydotool daemon when on Wayland (or when forcing ydotool). Use one user-owned daemon.
if command -v ydotoold >/dev/null 2>&1; then
  if [ -n "$BACKEND" ] && [ "$BACKEND" = "ydotool" ] || [ "$XDG_SESSION_TYPE" = "wayland" ]; then
    pkill -x ydotoold 2>/dev/null
    sleep 0.5
    (ydotoold 2>/dev/null &)
    sleep 1
  fi
fi

./venv/bin/python laptop_server.py --user &
USER_PID=$!

# Wait until the user server creates the socket (in home dir)
SOCK="$HOME/.keyboardmouse.sock"
for i in 1 2 3 4 5 6 7 8 9 10; do
  [ -S "$SOCK" ] && break
  sleep 0.5
done
if [ ! -S "$SOCK" ]; then
  echo "User server did not create $SOCK in time."
  kill "$USER_PID" 2>/dev/null
  exit 1
fi

sudo ./venv/bin/python laptop_server.py --bt
cleanup
