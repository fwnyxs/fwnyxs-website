#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_DIR="$SCRIPT_DIR/python"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required in WSL Ubuntu. Install it with: sudo apt update && sudo apt install python3 python3-venv python3-pip"
  exit 1
fi

cd "$SCRIPT_DIR"
python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "$PYTHON_DIR/requirements.txt"

echo
echo "WSL setup complete."
echo "Next step: bash ./run-wsl.sh"
echo "Optional: copy wsl.env.example to .env and adjust Oracle settings."
