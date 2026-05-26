#!/usr/bin/env bash
# Minimal deploy script for Ubuntu VPS
set -euo pipefail

APP_DIR="/opt/etender-monitor"
PYTHON=python3

echo "Creating app dir: $APP_DIR"
sudo mkdir -p "$APP_DIR"
sudo chown "$USER":"$USER" "$APP_DIR"

echo "Copying repository files to $APP_DIR"
rsync -av --exclude '.git' --exclude '__pycache__' . "$APP_DIR/"

cd "$APP_DIR"

echo "Setting up Python venv"
$PYTHON -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Create environment file at $APP_DIR/.env with TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS"
cat > .env <<'ENV'
# Example:
# TELEGRAM_BOT_TOKEN=123456:ABC-DEF
# TELEGRAM_CHAT_IDS=1601481679,8248109069
ENV

echo "Created .env (edit it and fill your secrets)."

echo "Install systemd unit files (requires sudo)."
sudo cp parcer/etender_monitor.service /etc/systemd/system/
sudo cp parcer/etender_monitor.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now etender-monitor.timer

echo "Deployment complete. Check status with: sudo systemctl status etender-monitor.service"
