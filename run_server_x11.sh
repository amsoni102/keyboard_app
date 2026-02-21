#!/usr/bin/env bash
# Run the server on X11 (Xorg) so xdotool can control the screen.
# If you're on Wayland, this script tells you to switch to Xorg and exits.
cd "$(dirname "$0")"

SESSION="${XDG_SESSION_TYPE:-}"
if [ "$SESSION" = "wayland" ]; then
  echo "You are on Wayland. For the phone to control the laptop, use X11 (Xorg):"
  echo "  1. Log out"
  echo "  2. On the login screen, open the session menu and choose 'Ubuntu on Xorg'"
  echo "  3. Log in again"
  echo "  4. Run:  sudo apt install xdotool"
  echo "  5. Run:  ./run_server_x11.sh   or   ./run_server.sh"
  exit 1
fi

echo "Session: X11 (xdotool will control the screen)."
export DISPLAY="${DISPLAY:-:0}"
exec ./run_server.sh
