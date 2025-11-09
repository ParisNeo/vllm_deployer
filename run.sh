#!/bin/bash

# Color codes for better visibility
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}[*] Starting vLLM deployment...${NC}"
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
    echo -e "${RED}[!] ERROR: MODEL_LIST is empty in .env file${NC}"
    echo -e "${YELLOW}[!] Please add models to MODEL_LIST in the format: 'model1:config1.json,model2:config2.json'${NC}"
    echo -e "${YELLOW}[!] Example: MODEL_LIST='opt-1.3b:vllm_config.json'${NC}"
    exit 1
fi

# Check if MODEL_DIR exists
if [ ! -d "$MODEL_DIR" ]; then
    echo -e "${RED}[!] ERROR: Model directory does not exist: $MODEL_DIR${NC}"
    echo -e "${YELLOW}[!] Please create the directory or pull models using ./pull_model.sh${NC}"
    exit 1
fi

# Check if vLLM is installed
if ! command -v vllm &> /dev/null; then
    echo -e "${RED}[!] ERROR: vLLM command not found${NC}"
    echo -e "${YELLOW}[!] Please ensure the virtual environment is activated or vLLM is installed${NC}"
    exit 1
fi

# Parse and launch each model
MODEL_COUNT=0
PIDS=()

for entry in $(echo $MODEL_LIST | tr ',' '\n'); do
    MODEL=$(echo $entry | cut -d':' -f1)
    CONFIG=$(echo $entry | cut -d':' -f2)
    
    echo -e "${BLUE}[*] Processing model: $MODEL${NC}"
    echo "    - Config file: $CONFIG"
    
    MODEL_PATH="$MODEL_DIR/$MODEL"
    CONFIG_PATH="$MODEL_DIR/$MODEL/$CONFIG"
    
    # Check if model exists
    if [ ! -d "$MODEL_PATH" ]; then
        echo -e "${YELLOW}[!] WARNING: Model directory not found: $MODEL_PATH${NC}"
        echo -e "${YELLOW}[!] Skipping this model...${NC}"
        continue
    fi
    
    # Check if config exists
    if [ ! -f "$CONFIG_PATH" ]; then
        echo -e "${YELLOW}[!] WARNING: Config file not found: $CONFIG_PATH${NC}"
        echo -e "${YELLOW}[!] Skipping this model...${NC}"
        continue
    fi
    
    echo -e "${GREEN}[*] Starting vLLM server for model: $MODEL${NC}"
    echo "    - Model path: $MODEL_PATH"
    echo "    - Config: $CONFIG_PATH"
    echo "    - Port: $VLLM_PORT"
    echo ""
    
    # Launch vLLM in background
    vllm serve "$MODEL_PATH" --config "$CONFIG_PATH" --port $VLLM_PORT 2>&1 | sed "s/^/[$MODEL] /" &
    VLLM_PID=$!
    PIDS+=($VLLM_PID)
    
    echo -e "${GREEN}[*] vLLM server started with PID: $VLLM_PID${NC}"
    MODEL_COUNT=$((MODEL_COUNT + 1))
    echo ""
    
    # Small delay to avoid port conflicts if multiple models
    sleep 1
done

if [ $MODEL_COUNT -eq 0 ]; then
    echo -e "${RED}[!] ERROR: No models were successfully loaded${NC}"
    echo -e "${YELLOW}[!] Please check your .env configuration and model files${NC}"
    exit 1
fi

echo -e "${GREEN}[*] Successfully started $MODEL_COUNT model(s)${NC}"
echo -e "${GREEN}[*] vLLM is running. Press Ctrl+C to stop all servers.${NC}"
echo "================================================"
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
