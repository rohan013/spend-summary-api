#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="personal-finance"
UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if ! command -v systemctl &>/dev/null; then
    echo "ERROR: systemctl not found." >&2
    exit 1
fi

if [[ ! -f "$UNIT_FILE" ]]; then
    echo "Service ${SERVICE_NAME} is not installed. Nothing to do."
    exit 0
fi

echo "Stopping and disabling ${SERVICE_NAME} ..."
sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || true

echo "Removing unit file $UNIT_FILE ..."
sudo rm -f "$UNIT_FILE"

sudo systemctl daemon-reload

echo "Done. venv and .env were left in place."
echo "To also remove them: rm -rf venv .env"
