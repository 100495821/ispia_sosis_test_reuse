#!/usr/bin/env bash
# setup.sh — Create a virtual environment and install all dependencies.
set -euo pipefail

VENV_DIR=".venv"

echo "Creating virtual environment in ${VENV_DIR}/ ..."
python3 -m venv "${VENV_DIR}"

echo "Installing dependencies ..."
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r requirements.txt

echo ""
echo "Setup complete. Activate the environment with:"
echo "  source ${VENV_DIR}/bin/activate"
