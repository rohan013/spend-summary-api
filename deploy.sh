#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="spend-summary"
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

echo "Installing dependencies from uv.lock into $VENV_DIR ..."
UV_PROJECT_ENVIRONMENT="$VENV_DIR" uv sync --quiet --frozen --no-dev --project "$REPO_DIR"

DEPLOY_USER="$(whoami)"
echo "Writing systemd unit file (requires sudo) ..."
sudo tee "$UNIT_FILE" > /dev/null <<EOF
[Unit]
Description=Spend summary API
After=network.target

[Service]
Type=simple
User=${DEPLOY_USER}
WorkingDirectory=${REPO_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${GUNICORN} -w 2 -b 127.0.0.1:${PORT} app:app
Restart=on-failure
RestartSec=5

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${REPO_DIR}

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
echo "  http://localhost:${PORT}"
