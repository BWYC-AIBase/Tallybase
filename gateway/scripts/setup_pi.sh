#!/bin/bash
# Raspberry Pi setup script for ATEM LoRa Tally Gateway
set -euo pipefail

echo "=== ATEM LoRa Tally Gateway Setup ==="

echo "Gateway uses REYAX RYLR998 over UART (/dev/serial0 by default)."
echo "Enable the Pi serial port in raspi-config -> Interface Options -> Serial Port:"
echo "  login shell over serial: No"
echo "  serial hardware: Yes"

TALLY_USER="${SUDO_USER:-$USER}"
INSTALL_DIR="${TALLY_HOME:-/home/${TALLY_USER}/tallybase}"
VENV_DIR="${INSTALL_DIR}/.venv"

echo "Install gateway files to ${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}"

if ! python3 -m venv --help >/dev/null 2>&1; then
  echo "Installing python3-venv..."
  sudo apt-get update
  sudo apt-get install -y python3-venv
fi

python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install -r "$(dirname "$0")/../requirements.txt"

echo "Copy tallybase/ contents to ${INSTALL_DIR} manually or via git pull."
echo "Set ATEM IP from the Web UI after the service starts."

SERVICE_FILE="$(dirname "$0")/../../deploy/tally-gateway.service"
if [ -f "${SERVICE_FILE}" ]; then
  sudo sed \
    -e "s|__TALLY_HOME__|${INSTALL_DIR}|g" \
    -e "s|__TALLY_USER__|${TALLY_USER}|g" \
    "${SERVICE_FILE}" | \
    sudo tee /etc/systemd/system/tally-gateway.service >/dev/null
  sudo systemctl daemon-reload
  echo "Installed systemd service. Enable with:"
  echo "  sudo systemctl enable tally-gateway"
  echo "  sudo systemctl start tally-gateway"
fi

echo "Setup complete."
