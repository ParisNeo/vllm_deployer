#!/bin/bash

# Color codes for better visibility
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}vLLM Server Launcher${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}[*] Loading configuration from .env file...${NC}"

set -a
source "$(dirname "$0")/.env"
set +a

echo -e "${GREEN}[*] Configuration loaded:${NC}"
echo "    - Model directory: $MODEL_DIR"
echo "    - Model list: $MODEL_LIST"
echo "    - Port: $VLLM_PORT"
echo "    - Dev mode: $DEV_MODE"
echo ""

# Check if MODEL_LIST is empty
if [ -z "$MODEL_LIST" ]; then
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}ERROR: No Models Configured${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${YELLOW}Your MODEL_LIST in the .env file is empty.${NC}"
    echo -e "${YELLOW}You need to download and configure at least one model before running vLLM.${NC}"
    echo ""
    echo -e "${CYAN}──────────────────────────────────────${NC}"
    echo -e "${CYAN}STEP-BY-STEP GUIDE TO GET STARTED:${NC}"
    echo -e "${CYAN}──────────────────────────────────────${NC}"
    echo ""
    echo -e "${GREEN}Step 1: Choose a Model${NC}"
    echo ""
    echo "For beginners, we recommend starting with a small model:"
    echo ""
    echo -e "  ${BLUE}Small models (good for testing):${NC}"
    echo "    • facebook/opt-125m        - Very fast, minimal GPU needed (~250MB)"
    echo "    • facebook/opt-1.3b        - Still fast, better quality (~2.5GB)"
    echo "    • microsoft/phi-2          - High quality small model (~5GB)"
    echo ""
    echo -e "  ${BLUE}Medium models (production ready):${NC}"
    echo "    • mistralai/Mistral-7B-Instruct-v0.2  - Excellent balance (~14GB)"
    echo "    • meta-llama/Llama-2-7b-chat-hf       - Very capable (~14GB)"
    echo ""
    echo -e "${YELLOW}💡 Tip: Start with facebook/opt-125m to verify everything works!${NC}"
    echo ""
    echo -e "${CYAN}──────────────────────────────────────${NC}"
    echo ""
    echo -e "${GREEN}Step 2: Download the Model${NC}"
    echo ""
    echo "Run this command to download a model (example with opt-125m):"
    echo ""
    echo -e "  ${BLUE}./pull_model.sh facebook/opt-125m${NC}"
    echo ""
    echo "This will:"
    echo "  ✓ Download the model from Hugging Face"
    echo "  ✓ Create a configuration file"
    echo "  ✓ Tell you what to do next"
    echo ""
    echo -e "${YELLOW}⏱  Note: Downloading may take a few minutes depending on model size${NC}"
    echo ""
    echo "To see all available options and more model suggestions:"
    echo -e "  ${BLUE}./pull_model.sh${NC}  (run without arguments)"
    echo ""
    echo -e "${CYAN}──────────────────────────────────────${NC}"
    echo ""
    echo -e "${GREEN}Step 3: Update Your Configuration${NC}"
    echo ""
    echo "After downloading, edit the .env file:"
    echo ""
    echo -e "  ${BLUE}nano .env${NC}"
    echo ""
    echo "Find the MODEL_LIST line and update it. For example:"
    echo ""
    echo "  Before: MODEL_LIST=''"
    echo -e "  After:  ${GREEN}MODEL_LIST='opt-125m:vllm_config.json'${NC}"
    echo ""
    echo "For multiple models, use comma separation:"
    echo -e "  ${GREEN}MODEL_LIST='opt-125m:vllm_config.json,phi-2:vllm_config.json'${NC}"
    echo ""
    echo "Save and exit (Ctrl+O, Enter, Ctrl+X in nano)"
    echo ""
    echo -e "${CYAN}──────────────────────────────────────${NC}"
    echo ""
    echo -e "${GREEN}Step 4: Run Again${NC}"
    echo ""
    echo "Once configured, run this script again:"
    echo ""
    echo -e "  ${BLUE}./run.sh${NC}"
    echo ""
    echo -e "${CYAN}──────────────────────────────────────${NC}"
    echo ""
    echo -e "${YELLOW}QUICK START (Copy & Paste):${NC}"
    echo ""
    echo -e "${BLUE}# Download a test model${NC}"
    echo "./pull_model.sh facebook/opt-125m"
    echo ""
    echo -e "${BLUE}# Edit configuration${NC}"
    echo "nano .env"
    echo -e "${BLUE}# Change MODEL_LIST='' to MODEL_LIST='opt-125m:vllm_config.json'${NC}"
    echo ""
    echo -e "${BLUE}# Run the server${NC}"
    echo "./run.sh"
    echo ""
    echo -e "${CYAN}──────────────────────────────────────${NC}"
    echo ""
    echo -e "${YELLOW}Need more help?${NC}"
    echo "  • See README.md for detailed documentation"
    echo "  • Browse models: https://huggingface.co/models"
    echo "  • vLLM docs: https://docs.vllm.ai"
    echo ""
    echo -e "${RED}========================================${NC}"
    exit 1
fi

# Check if MODEL_DIR exists
if [ ! -d "$MODEL_DIR" ]; then
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}ERROR: Model Directory Not Found${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${YELLOW}The model directory doesn't exist: $MODEL_DIR${NC}"
    echo ""
    echo "This directory should contain your downloaded models."
    echo ""
    echo -e "${GREEN}To fix this:${NC}"
    echo ""
    echo "1. Download a model using:"
    echo -e "   ${BLUE}./pull_model.sh facebook/opt-125m${NC}"
    echo ""
    echo "2. Or create the directory and download manually:"
    echo -e "   ${BLUE}mkdir -p $MODEL_DIR${NC}"
    echo ""
    echo -e "${RED}========================================${NC}"
    exit 1
fi

# Check if vLLM is installed
if ! command -v vllm &> /dev/null; then
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}ERROR: vLLM Not Found${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${YELLOW}The vLLM command is not available.${NC}"
    echo ""
    echo "This usually means the virtual environment is not activated."
    echo ""
    echo -e "${GREEN}To fix this:${NC}"
    echo ""
    echo "1. Activate the virtual environment:"
    echo -e "   ${BLUE}source venv/bin/activate${NC}"
    echo ""
    echo "2. Verify vLLM is installed:"
    echo -e "   ${BLUE}vllm --version${NC}"
    echo ""
    echo "3. If not installed, reinstall:"
    echo -e "   ${BLUE}pip install vllm${NC}"
    echo ""
    echo -e "${RED}========================================${NC}"
    exit 1
fi

# Parse and launch each model
MODEL_COUNT=0
PIDS=()
FAILED_MODELS=0

echo -e "${BLUE}[*] Processing models from MODEL_LIST...${NC}"
echo ""

for entry in $(echo $MODEL_LIST | tr ',' '\n'); do
    MODEL=$(echo $entry | cut -d':' -f1)
    CONFIG=$(echo $entry | cut -d':' -f2)
    
    echo -e "${CYAN}──────────────────────────────────────${NC}"
    echo -e "${BLUE}[*] Processing model: $MODEL${NC}"
    echo "    - Config file: $CONFIG"
    
    MODEL_PATH="$MODEL_DIR/$MODEL"
    CONFIG_PATH="$MODEL_DIR/$MODEL/$CONFIG"
    
    # Check if model exists
    if [ ! -d "$MODEL_PATH" ]; then
        echo -e "${YELLOW}[!] WARNING: Model directory not found${NC}"
        echo "    Expected location: $MODEL_PATH"
        echo ""
        echo -e "${GREEN}To download this model:${NC}"
        echo -e "    ${BLUE}./pull_model.sh <huggingface_model_name>${NC}"
        echo ""
        echo "Example (if this is opt-125m):"
        echo -e "    ${BLUE}./pull_model.sh facebook/opt-125m${NC}"
        echo ""
        echo -e "${YELLOW}Skipping this model...${NC}"
        echo ""
        FAILED_MODELS=$((FAILED_MODELS + 1))
        continue
    fi
    
    # Check if config exists
    if [ ! -f "$CONFIG_PATH" ]; then
        echo -e "${YELLOW}[!] WARNING: Config file not found${NC}"
        echo "    Expected location: $CONFIG_PATH"
        echo ""
        echo "The configuration file should have been created by pull_model.sh"
        echo ""
        echo -e "${GREEN}To create a default config:${NC}"
        cat <<EOF
cat > "$CONFIG_PATH" <<'CONFIGEOF'
{
  "max_model_len": 2048,
  "gpu_memory_utilization": 0.9,
  "tensor_parallel_size": 1,
  "dtype": "auto",
  "quantization": null
}
CONFIGEOF
EOF
        echo ""
        echo -e "${YELLOW}Skipping this model...${NC}"
        echo ""
        FAILED_MODELS=$((FAILED_MODELS + 1))
        continue
    fi
    
    echo -e "${GREEN}[✓] Model found${NC}"
    echo -e "${GREEN}[✓] Config found${NC}"
    echo ""
    echo -e "${GREEN}[*] Starting vLLM server for: $MODEL${NC}"
    echo "    - Model path: $MODEL_PATH"
    echo "    - Config: $CONFIG_PATH"
    echo "    - Port: $VLLM_PORT"
    echo ""
    
    # Launch vLLM in background
    vllm serve "$MODEL_PATH" --config "$CONFIG_PATH" --port $VLLM_PORT 2>&1 | sed "s/^/[$MODEL] /" &
    VLLM_PID=$!
    PIDS+=($VLLM_PID)
    
    echo -e "${GREEN}[✓] Server started (PID: $VLLM_PID)${NC}"
    MODEL_COUNT=$((MODEL_COUNT + 1))
    echo ""
    
    # Small delay to avoid port conflicts if multiple models
    sleep 1
done

echo -e "${CYAN}========================================${NC}"

if [ $MODEL_COUNT -eq 0 ]; then
    echo -e "${RED}ERROR: No Models Successfully Loaded${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
    echo -e "${YELLOW}Summary:${NC}"
    echo "  - Models in config: $(echo $MODEL_LIST | tr ',' '\n' | wc -l)"
    echo "  - Models loaded: $MODEL_COUNT"
    echo "  - Models failed: $FAILED_MODELS"
    echo ""
    echo -e "${YELLOW}All configured models failed to load.${NC}"
    echo ""
    echo -e "${GREEN}What to do:${NC}"
    echo ""
    echo "1. Check that models are downloaded:"
    echo -e "   ${BLUE}ls -la $MODEL_DIR/${NC}"
    echo ""
    echo "2. Download missing models:"
    echo -e "   ${BLUE}./pull_model.sh <model_name>${NC}"
    echo ""
    echo "3. Verify your MODEL_LIST in .env matches downloaded models"
    echo ""
    echo "4. For help choosing models:"
    echo -e "   ${BLUE}./pull_model.sh${NC}  (run without arguments)"
    echo ""
    echo -e "${CYAN}========================================${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Successfully Started $MODEL_COUNT Model(s)${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${GREEN}vLLM is now running!${NC}"
echo ""
echo "Access your model(s) at:"
echo -e "  ${BLUE}http://localhost:$VLLM_PORT${NC}"
echo ""
echo "Test with curl:"
echo -e "  ${BLUE}curl http://localhost:$VLLM_PORT/v1/models${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all servers${NC}"
echo ""
echo -e "${CYAN}──────────────────────────────────────${NC}"
echo "Server logs:"
echo -e "${CYAN}──────────────────────────────────────${NC}"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}[*] Shutting down vLLM servers...${NC}"
    for pid in "${PIDS[@]}"; do
        if kill -0 $pid 2>/dev/null; then
            echo "    - Stopping process $pid"
            kill $pid
        fi
    done
    echo -e "${GREEN}[*] All servers stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for all background processes
wait
