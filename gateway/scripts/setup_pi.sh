#!/bin/bash
# Raspberry Pi Docker setup script for ATEM LoRa Tally Gateway
set -euo pipefail

echo "=== ATEM LoRa Tally Gateway Setup ==="

echo "Gateway uses REYAX RYLR998 over UART (/dev/serial0 by default)."
echo "Enable the Pi serial port in raspi-config -> Interface Options -> Serial Port:"
echo "  login shell over serial: No"
echo "  serial hardware: Yes"

TALLY_USER="${SUDO_USER:-$USER}"
INSTALL_DIR="${TALLY_HOME:-/home/${TALLY_USER}/tallybase}"

if ! command -v curl >/dev/null 2>&1; then
  echo "Installing curl..."
  sudo apt-get update
  sudo apt-get install -y curl
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not found. Installing Docker..."
  curl -fsSL https://get.docker.com | sudo sh
fi

if ! sudo docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin is required but was not found."
  echo "Install it with your OS package manager, then rerun this script."
  exit 1
fi

if ! groups "${TALLY_USER}" | grep -q '\bdocker\b'; then
  echo "Adding ${TALLY_USER} to docker group."
  sudo usermod -aG docker "${TALLY_USER}" || true
  echo "Log out and log back in to use docker without sudo."
fi

if [ ! -f "${INSTALL_DIR}/docker-compose.yml" ]; then
  echo "Cannot find ${INSTALL_DIR}/docker-compose.yml"
  echo "Clone or copy this repo to ${INSTALL_DIR}, or set TALLY_HOME before running this script."
  exit 1
fi

cd "${INSTALL_DIR}"
mkdir -p data

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
fi

WEB_PORT="${FLASK_PORT:-5000}"
if [ -f ".env" ]; then
  WEB_PORT="$(grep -E '^FLASK_PORT=' .env | tail -n 1 | cut -d '=' -f 2- || true)"
  WEB_PORT="${WEB_PORT:-5000}"
fi

sudo docker compose build
sudo docker compose up -d

echo "Gateway container started."
echo "Web UI: http://<pi-ip>:${WEB_PORT}"
echo "View logs with:"
echo "  cd ${INSTALL_DIR} && sudo docker compose logs -f"

echo "Setup complete."
