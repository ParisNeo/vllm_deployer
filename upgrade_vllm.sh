#!/bin/bash

# Usage: bash upgrade_vllm.sh [install_dir]

INSTALL_DIR="${1:-$(pwd)}"
VENV_DIR="$INSTALL_DIR/venv"
ENV_FILE="$INSTALL_DIR/.env"
SERVICE_NAME="vllm"

if [ ! -d "$VENV_DIR" ]; then
    echo "[!] Virtual environment not found at $VENV_DIR"
    echo "[!] Please run install_vllm.sh first"
    exit 1
fi

# Source the venv
source "$VENV_DIR/bin/activate"

# Check if dev mode from .env
DEV_MODE=false
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
fi

echo "[*] Upgrading vLLM in: $INSTALL_DIR"
echo "[*] Dev mode: $DEV_MODE"

# Stop service if running
SERVICE_WAS_ACTIVE=false
if systemctl is-active --quiet $SERVICE_NAME 2>/dev/null; then
    echo "[*] Stopping $SERVICE_NAME service..."
    systemctl stop $SERVICE_NAME
    SERVICE_WAS_ACTIVE=true
fi

# Upgrade vllm
if [ "$DEV_MODE" = true ]; then
    echo "[*] Upgrading vLLM from source (dev version)..."
    cd "$INSTALL_DIR/vllm-source"
    git pull
    pip install -e . --upgrade
    cd "$INSTALL_DIR"
else
    echo "[*] Upgrading vLLM stable version..."
    pip install --upgrade vllm
fi

# Restart service if it was active
if [ "$SERVICE_WAS_ACTIVE" = true ]; then
    echo "[*] Restarting $SERVICE_NAME service..."
    systemctl start $SERVICE_NAME
fi

echo "[*] Upgrade complete."
if systemctl is-enabled --quiet $SERVICE_NAME 2>/dev/null; then
    echo "[*] Check service status with: systemctl status $SERVICE_NAME"
fi
