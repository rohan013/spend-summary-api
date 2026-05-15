#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="personal-finance"
PORT=8317

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$SCRIPT_DIR"
VENV_DIR="$REPO_DIR/venv"
ENV_FILE="$REPO_DIR/.env"
UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
GUNICORN="$VENV_DIR/bin/gunicorn"

if ! command -v systemctl &>/dev/null; then
    echo "ERROR: systemctl not found. Requires a systemd-based OS (Ubuntu/Debian)." >&2
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: .env file not found at $ENV_FILE" >&2
    echo "       Copy .env.example to .env and fill in your Plaid credentials:" >&2
    echo "         cp $REPO_DIR/.env.example $REPO_DIR/.env" >&2
    exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment at $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
fi

echo "Installing/upgrading dependencies ..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$REPO_DIR/requirements.txt"

DEPLOY_USER="$(whoami)"
echo "Writing systemd unit file (requires sudo) ..."
sudo tee "$UNIT_FILE" > /dev/null <<EOF
[Unit]
Description=Personal Finance Flask App
After=network.target

[Service]
Type=simple
User=${DEPLOY_USER}
WorkingDirectory=${REPO_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${GUNICORN} -w 2 -b 0.0.0.0:${PORT} app:app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

sleep 2
sudo systemctl is-active --quiet "$SERVICE_NAME" \
    && echo "Service is running." \
    || echo "WARNING: service may not have started. Check: sudo journalctl -u $SERVICE_NAME -n 50" >&2

echo ""
echo "Deployed. App available at:"
echo "  http://$(hostname -I | awk '{print $1}'):${PORT}"
echo "  http://localhost:${PORT}"
