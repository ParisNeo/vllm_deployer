#!/bin/bash

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install additional dependencies
echo "[*] Installing required packages..."
pip install fastapi uvicorn httpx psutil gputil pydantic -q

# Check for admin password
if [ -z "$VLLM_ADMIN_PASSWORD_HASH" ]; then
    echo ""
    echo "========================================="
    echo "⚠️  SECURITY WARNING"
    echo "========================================="
    echo ""
    echo "Using default password: admin123"
    echo ""
    echo "To set a custom password:"
    echo "  1. Generate hash: echo -n 'your_password' | sha256sum"
    echo "  2. Set environment variable:"
    echo "     export VLLM_ADMIN_PASSWORD_HASH='your_hash'"
    echo ""
    echo "========================================="
    echo ""
fi

# Start the manager
echo "[*] Starting vLLM Manager Pro..."
echo "[*] Web UI: http://localhost:9000"
echo "[*] Username: admin"
echo "[*] Password: admin123 (change this!)"
echo ""

python vllm_manager.py
