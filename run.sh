#!/bin/bash

#############################################
# vLLM Manager Launcher
# Starts the web UI and management backend
#############################################

# Color codes for output
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}vLLM Manager Launcher${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Activate virtual environment
if [ -d "venv" ]; then
    echo "[*] Activating virtual environment..."
    source venv/bin/activate
else
    echo -e "${YELLOW}[!] Virtual environment not found. Please run install_vllm.sh first.${NC}"
    exit 1
fi

# Check for admin password hash
if [ -z "$VLLM_ADMIN_PASSWORD_HASH" ]; then
    echo -e "${YELLOW}=========================================${NC}"
    echo -e "${YELLOW}⚠️  SECURITY WARNING${NC}"
    echo -e "${YELLOW}=========================================${NC}"
    echo ""
    echo "You are using the default password: admin123"
    echo ""
    echo "For production, please set a custom password:"
    echo "  1. Generate hash:"
    echo -e "     ${BLUE}echo -n 'your_secure_password' | sha256sum${NC}"
    echo "  2. Set environment variable:"
    echo -e "     ${BLUE}export VLLM_ADMIN_PASSWORD_HASH='your_hash_here'${NC}"
    echo ""
    echo -e "${YELLOW}=========================================${NC}"
    echo ""
fi

# Start the manager
echo "[*] Starting vLLM Manager..."
echo "[*] Web UI available at: http://localhost:9000"
echo "[*]"
echo "[*] Default credentials:"
echo "[*]   Username: admin"
echo "[*]   Password: admin123 (unless VLLM_ADMIN_PASSWORD_HASH is set)"
echo ""
echo "[*] Press Ctrl+C to stop the manager."
echo ""

python vllm_manager.py
