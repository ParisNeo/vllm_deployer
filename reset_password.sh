#!/bin/bash

#############################################
# vLLM Manager Password Reset Utility
# Securely resets the admin password.
#############################################

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}vLLM Manager Password Reset Utility${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Find .env file
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}[✗] .env file not found!${NC}"
    echo "Please run this script from the vLLM Deployer installation directory."
    exit 1
fi

# Prompt for new password securely
read -s -p "Enter new admin password: " NEW_PASSWORD
echo ""
read -s -p "Confirm new admin password: " CONFIRM_PASSWORD
echo ""

# Validate passwords
if [ -z "$NEW_PASSWORD" ]; then
    echo -e "${RED}[✗] Password cannot be empty. Aborting.${NC}"
    exit 1
fi

if [ "$NEW_PASSWORD" != "$CONFIRM_PASSWORD" ]; then
    echo -e "${RED}[✗] Passwords do not match. Aborting.${NC}"
    exit 1
fi

# Generate SHA256 hash
echo "[*] Generating password hash..."
PASSWORD_HASH=$(echo -n "$NEW_PASSWORD" | sha256sum | cut -d' ' -f1)

# Backup .env file
cp "$ENV_FILE" "${ENV_FILE}.bak"
echo "[*] .env file backed up to ${ENV_FILE}.bak"

# Update .env file
echo "[*] Updating .env file..."

# Check if the variable already exists
if grep -q "^VLLM_ADMIN_PASSWORD_HASH=" "$ENV_FILE"; then
    # Variable exists, replace it
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS sed
        sed -i '' "s|^VLLM_ADMIN_PASSWORD_HASH=.*|VLLM_ADMIN_PASSWORD_HASH='${PASSWORD_HASH}'|" "$ENV_FILE"
    else
        # Linux sed
        sed -i "s|^VLLM_ADMIN_PASSWORD_HASH=.*|VLLM_ADMIN_PASSWORD_HASH='${PASSWORD_HASH}'|" "$ENV_FILE"
    fi
    echo -e "${GREEN}[✓] Existing password hash updated.${NC}"
else
    # Variable does not exist, append it
    echo "" >> "$ENV_FILE"
    echo "VLLM_ADMIN_PASSWORD_HASH='${PASSWORD_HASH}'" >> "$ENV_FILE"
    echo -e "${GREEN}[✓] Password hash added to .env file.${NC}"
fi

echo ""
echo -e "${GREEN}Password has been successfully reset!${NC}"
echo -e "${YELLOW}Please restart the vLLM manager for the new password to take effect.${NC}"
echo "  - If running directly: Stop with Ctrl+C and restart with ./run.sh"
echo "  - If running as a service: sudo systemctl restart vllm"
echo ""
