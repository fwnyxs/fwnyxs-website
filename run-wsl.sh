#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_DIR="$SCRIPT_DIR/python"
ENV_FILE="$SCRIPT_DIR/.env"
EXAMPLE_ENV_FILE="$SCRIPT_DIR/wsl.env.example"

if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
elif [ -f "$EXAMPLE_ENV_FILE" ]; then
  echo "Using example WSL environment values from $EXAMPLE_ENV_FILE"
  # shellcheck disable=SC1090
  source "$EXAMPLE_ENV_FILE"
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Virtual environment not found. Run: bash ./setup-wsl.sh"
  exit 1
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
cd "$PYTHON_DIR"

export ORACLE_USER="${ORACLE_USER:-system}"
export ORACLE_PASSWORD="${ORACLE_PASSWORD:-Oracle123}"
export PORT="${PORT:-5000}"

python app.py
