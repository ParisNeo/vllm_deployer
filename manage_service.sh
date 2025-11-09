#!/bin/bash

# Usage: bash manage_service.sh [install|uninstall] [install_dir]

ACTION="$1"
INSTALL_DIR="${2:-$(pwd)}"
VENV_DIR="$INSTALL_DIR/venv"
SERVICE_NAME="vllm"

if [ -z "$ACTION" ]; then
    echo "Usage: bash manage_service.sh [install|uninstall] [install_dir]"
    echo "  install   - Install and enable the vLLM systemd service"
    echo "  uninstall - Stop, disable, and remove the vLLM systemd service"
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "[!] Virtual environment not found at $VENV_DIR"
    echo "[!] Please run install_vllm.sh first"
    exit 1
fi

case "$ACTION" in
    install)
        echo "[*] Installing systemd service: $SERVICE_NAME"
        
        cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOL
[Unit]
Description=vLLM serving via run.sh
After=network.target

[Service]
Type=simple
Restart=always
WorkingDirectory=${INSTALL_DIR}
Environment="VIRTUAL_ENV=${VENV_DIR}"
ExecStart=${VENV_DIR}/bin/bash ${INSTALL_DIR}/run.sh
User=$(whoami)
Group=$(id -gn)

[Install]
WantedBy=multi-user.target
EOL

        systemctl daemon-reload
        systemctl enable $SERVICE_NAME
        systemctl start $SERVICE_NAME
        
        echo "[*] Service installed and started."
        echo "[*] Check status with: systemctl status $SERVICE_NAME"
        echo "[*] View logs with: journalctl -u $SERVICE_NAME -f"
        ;;
        
    uninstall)
        echo "[*] Uninstalling systemd service: $SERVICE_NAME"
        
        # Stop the service if running
        if systemctl is-active --quiet $SERVICE_NAME; then
            echo "[*] Stopping service..."
            systemctl stop $SERVICE_NAME
        fi
        
        # Disable the service
        if systemctl is-enabled --quiet $SERVICE_NAME 2>/dev/null; then
            echo "[*] Disabling service..."
            systemctl disable $SERVICE_NAME
        fi
        
        # Remove service file
        if [ -f "/etc/systemd/system/${SERVICE_NAME}.service" ]; then
            echo "[*] Removing service file..."
            rm "/etc/systemd/system/${SERVICE_NAME}.service"
        fi
        
        # Reload systemd
        systemctl daemon-reload
        systemctl reset-failed 2>/dev/null
        
        echo "[*] Service uninstalled."
        ;;
        
    *)
        echo "[!] Invalid action: $ACTION"
        echo "Usage: bash manage_service.sh [install|uninstall] [install_dir]"
        exit 1
        ;;
esac
