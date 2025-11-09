#!/bin/bash

# Usage: bash install_vllm.sh [--dev] [install_dir] [optional_model_dir]

DEV_MODE=false
if [ "$1" == "--dev" ]; then
    DEV_MODE=true
    shift
fi

INSTALL_DIR="${1:-$(pwd)}"
MODEL_DIR="${2:-$INSTALL_DIR/models}"
VENV_DIR="$INSTALL_DIR/venv"

# Create install directory if missing
mkdir -p "$INSTALL_DIR"
mkdir -p "$MODEL_DIR"

echo "[*] Using install directory: $INSTALL_DIR"
echo "[*] Using model directory: $MODEL_DIR"
echo "[*] Dev mode: $DEV_MODE"

# 1. Create virtual environment
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# 2. Install vllm
pip install --upgrade pip

if [ "$DEV_MODE" = true ]; then
    echo "[*] Installing vLLM from source (dev version)..."
    cd "$INSTALL_DIR"
    git clone https://github.com/vllm-project/vllm.git vllm-source
    cd vllm-source
    pip install -e .
    cd "$INSTALL_DIR"
else
    echo "[*] Installing vLLM stable version..."
    pip install vllm
fi

# 3. Copy runner and puller scripts into install_dir
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/run.sh" "$SCRIPT_DIR/pull_model.sh" "$SCRIPT_DIR/manage_service.sh" "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/run.sh" "$INSTALL_DIR/pull_model.sh" "$INSTALL_DIR/manage_service.sh"

# 4. Setup .env file
cat > "$INSTALL_DIR/.env" <<EOL
MODEL_DIR=$MODEL_DIR
MODEL_LIST=''
VLLM_PORT=8000
DEV_MODE=$DEV_MODE
EOL

echo "[*] Installation complete."
echo "[*] To test manually, run: cd $INSTALL_DIR && ./run.sh"
echo "[*] To install as a systemd service, run: bash $INSTALL_DIR/manage_service.sh install"
echo "[*] To upgrade in the future, run: bash upgrade_vllm.sh $INSTALL_DIR"
