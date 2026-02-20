#!/usr/bin/env bash
# Create and set up a Python virtual environment for the laptop server.

set -e
cd "$(dirname "$0")"
VENV_DIR="${1:-venv}"

if ! python3 -m venv --help &>/dev/null; then
    echo "Error: python3-venv is not installed."
    echo "On Debian/Ubuntu run: sudo apt install python3-venv"
    exit 1
fi

# Remove broken or existing venv so we get a clean one
[[ -d "$VENV_DIR" ]] && rm -rf "$VENV_DIR"

echo "Creating virtual environment in $VENV_DIR ..."
if ! python3 -m venv "$VENV_DIR" 2>&1; then
    rm -rf "$VENV_DIR"
    PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "3")
    echo ""
    echo "Virtual environment failed (often due to missing ensurepip)."
    echo "On Debian/Ubuntu, install the venv package for your Python version:"
    echo "  sudo apt install python${PYVER}-venv"
    echo ""
    echo "Then run this script again: ./setup_venv.sh"
    exit 1
fi

echo "Activating and installing dependencies ..."
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
if [[ "$(uname)" == Linux ]]; then
    echo "On Linux, PyBluez needs: build-essential, libbluetooth-dev, python3-dev"
    echo "  sudo apt install build-essential libbluetooth-dev python3-dev"
fi
pip install -r requirements.txt

echo ""
echo "Done. To activate the virtual environment, run:"
echo "  source $VENV_DIR/bin/activate"
echo "Then start the server with:"
echo "  python laptop_server.py"
