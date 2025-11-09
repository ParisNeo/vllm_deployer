#!/bin/bash

#############################################
# vLLM Server Runner
# Launches vLLM models with YAML configuration
#############################################

# Color codes for better visibility
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

#############################################
# Header
#############################################

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}vLLM Server Launcher${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

#############################################
# Load Configuration
#############################################

echo -e "${BLUE}[*] Loading configuration from .env file...${NC}"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}[✗] .env file not found!${NC}"
    echo ""
    echo "Please ensure you're running this script from the installation directory."
    echo "Or create a .env file with required configuration."
    exit 1
fi

# Source the .env file
set -a
source "$(dirname "$0")/.env"
set +a

echo -e "${GREEN}[✓] Configuration loaded${NC}"
echo ""

#############################################
# Display Configuration
#############################################

echo -e "${CYAN}Current Configuration:${NC}"
echo "────────────────────────────────────────"
echo "  Model directory:  $MODEL_DIR"
echo "  Model list:       ${MODEL_LIST:-<empty>}"
echo "  Default port:     $VLLM_PORT"
echo "  Development mode: $DEV_MODE"
echo ""

#############################################
# Check if MODEL_LIST is Empty
#############################################

if [ -z "$MODEL_LIST" ]; then
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}ERROR: No Models Configured${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${YELLOW}Your MODEL_LIST in the .env file is empty.${NC}"
    echo -e "${YELLOW}You need to download and configure at least one model.${NC}"
    echo ""
    echo -e "${CYAN}──────────────────────────────────────${NC}"
    echo -e "${CYAN}STEP-BY-STEP GUIDE TO GET STARTED${NC}"
    echo -e "${CYAN}──────────────────────────────────────${NC}"
    echo ""
    echo -e "${GREEN}Step 1: Choose a Model${NC}"
    echo ""
    echo "For beginners, start with a small model:"
    echo ""
    echo -e "  ${BLUE}Small models (good for testing):${NC}"
    echo "    • facebook/opt-125m        - Very fast (~250MB)"
    echo "    • facebook/opt-1.3b        - Better quality (~2.5GB)"
    echo "    • microsoft/phi-2          - High quality (~5GB)"
    echo ""
    echo -e "  ${BLUE}Medium models (production ready):${NC}"
    echo "    • mistralai/Mistral-7B-Instruct-v0.2  (~14GB)"
    echo "    • meta-llama/Llama-2-7b-chat-hf       (~14GB)"
    echo ""
    echo -e "${YELLOW}💡 Tip: Start with facebook/opt-125m to verify setup!${NC}"
    echo ""
    echo -e "${CYAN}──────────────────────────────────────${NC}"
    echo ""
    echo -e "${GREEN}Step 2: Download the Model${NC}"
    echo ""
    echo "Run this command:"
    echo -e "  ${BLUE}./pull_model.sh facebook/opt-125m${NC}"
    echo ""
    echo "This will automatically:"
    echo "  ✓ Download the model"
    echo "  ✓ Create configuration"
    echo "  ✓ Update .env file"
    echo ""
    echo "To see all options:"
    echo -e "  ${BLUE}./pull_model.sh${NC}  (without arguments)"
    echo ""
    echo -e "${CYAN}──────────────────────────────────────${NC}"
    echo ""
    echo -e "${GREEN}Step 3: Run Again${NC}"
    echo ""
    echo "After downloading:"
    echo -e "  ${BLUE}./run.sh${NC}"
    echo ""
    echo -e "${CYAN}──────────────────────────────────────${NC}"
    echo ""
    echo -e "${YELLOW}QUICK START (Copy & Paste):${NC}"
    echo ""
    echo -e "${BLUE}# Download a test model${NC}"
    echo "./pull_model.sh facebook/opt-125m"
    echo ""
    echo -e "${BLUE}# Run the server${NC}"
    echo "./run.sh"
    echo ""
    echo -e "${CYAN}──────────────────────────────────────${NC}"
    echo ""
    echo -e "${YELLOW}Need more help?${NC}"
    echo "  • cat QUICKSTART.txt"
    echo "  • cat README.md"
    echo "  • Browse models: https://huggingface.co/models"
    echo ""
    echo -e "${RED}========================================${NC}"
    exit 1
fi

#############################################
# Validate Environment
#############################################

echo -e "${BLUE}[*] Validating environment...${NC}"
echo ""

# Check if MODEL_DIR exists
if [ ! -d "$MODEL_DIR" ]; then
    echo -e "${RED}[✗] Model directory not found: $MODEL_DIR${NC}"
    echo ""
    echo "Please create the directory or download models:"
    echo -e "  ${BLUE}./pull_model.sh facebook/opt-125m${NC}"
    exit 1
fi

echo -e "${GREEN}[✓] Model directory exists${NC}"

# Check if vLLM is installed
if ! command -v vllm &> /dev/null; then
    echo -e "${RED}[✗] vLLM command not found${NC}"
    echo ""
    echo "The vLLM command is not available. This usually means:"
    echo "  1. Virtual environment is not activated"
    echo "  2. vLLM is not installed"
    echo ""
    echo -e "${GREEN}To fix:${NC}"
    echo "  1. Activate the virtual environment:"
    echo -e "     ${BLUE}source venv/bin/activate${NC}"
    echo ""
    echo "  2. Verify vLLM is installed:"
    echo -e "     ${BLUE}vllm --version${NC}"
    echo ""
    echo "  3. If not installed:"
    echo -e "     ${BLUE}pip install vllm${NC}"
    exit 1
fi

VLLM_VERSION=$(vllm --version 2>&1 | head -n 1 || echo "unknown")
echo -e "${GREEN}[✓] vLLM is available${NC} ($VLLM_VERSION)"

echo ""

#############################################
# Helper Function: Parse YAML Config
#############################################

read_yaml_value() {
    local file="$1"
    local key="$2"
    local default="$3"
    
    if [ ! -f "$file" ]; then
        echo "$default"
        return
    fi
    
    # Parse YAML - handle both "key: value" and "key:value" formats
    # Also handle comments and empty values
    local value=$(grep "^[[:space:]]*${key}:" "$file" | \
                  head -n 1 | \
                  sed "s/^[[:space:]]*${key}:[[:space:]]*//" | \
                  sed 's/#.*//' | \
                  tr -d '"' | \
                  tr -d "'" | \
                  sed 's/[[:space:]]*$//')
    
    # Return value if not empty and not "null"
    if [ -n "$value" ] && [ "$value" != "null" ]; then
        echo "$value"
    else
        echo "$default"
    fi
}

#############################################
# Process Models
#############################################

echo -e "${BLUE}[*] Processing models from MODEL_LIST...${NC}"
echo ""

MODEL_COUNT=0
PIDS=()
FAILED_MODELS=0
PORT_OFFSET=0

for entry in $(echo $MODEL_LIST | tr ',' '\n'); do
    MODEL=$(echo $entry | cut -d':' -f1)
    CONFIG=$(echo $entry | cut -d':' -f2)
    
    echo -e "${CYAN}────────────────────────────────────────${NC}"
    echo -e "${MAGENTA}Model: $MODEL${NC}"
    echo -e "${CYAN}────────────────────────────────────────${NC}"
    
    MODEL_PATH="$MODEL_DIR/$MODEL"
    CONFIG_PATH="$MODEL_DIR/$MODEL/$CONFIG"
    
    # Assign unique port for each model
    CURRENT_PORT=$((VLLM_PORT + PORT_OFFSET))
    PORT_OFFSET=$((PORT_OFFSET + 1))
    
    #############################################
    # Validate Model Exists
    #############################################
    
    if [ ! -d "$MODEL_PATH" ]; then
        echo -e "${RED}[✗] Model directory not found${NC}"
        echo "    Expected: $MODEL_PATH"
        echo ""
        echo -e "${YELLOW}To download this model:${NC}"
        
        # Try to guess the full model name
        if [[ $MODEL == *"/"* ]]; then
            # Already has org/model format
            echo -e "  ${BLUE}./pull_model.sh $MODEL${NC}"
        else
            # Just the model name, provide examples
            echo "  Example (if this is opt-125m):"
            echo -e "    ${BLUE}./pull_model.sh facebook/opt-125m${NC}"
            echo ""
            echo "  Or browse models:"
            echo -e "    ${BLUE}./pull_model.sh${NC}  (shows available models)"
        fi
        echo ""
        FAILED_MODELS=$((FAILED_MODELS + 1))
        continue
    fi
    
    echo -e "${GREEN}[✓] Model directory found${NC}"
    
    #############################################
    # Load Configuration
    #############################################
    
    if [ -f "$CONFIG_PATH" ]; then
        echo -e "${GREEN}[✓] Configuration file found${NC}"
        echo "    $CONFIG_PATH"
        echo ""
        
        # Parse YAML configuration
        MAX_MODEL_LEN=$(read_yaml_value "$CONFIG_PATH" "max-model-len" "2048")
        GPU_MEMORY=$(read_yaml_value "$CONFIG_PATH" "gpu-memory-utilization" "0.9")
        TENSOR_PARALLEL=$(read_yaml_value "$CONFIG_PATH" "tensor-parallel-size" "1")
        DTYPE=$(read_yaml_value "$CONFIG_PATH" "dtype" "auto")
        QUANTIZATION=$(read_yaml_value "$CONFIG_PATH" "quantization" "")
        MAX_NUM_SEQS=$(read_yaml_value "$CONFIG_PATH" "max-num-seqs" "")
        ENABLE_PREFIX_CACHE=$(read_yaml_value "$CONFIG_PATH" "enable-prefix-caching" "")
        
        echo -e "${BLUE}Configuration:${NC}"
        echo "  • Max model length:      $MAX_MODEL_LEN"
        echo "  • GPU memory utilization: $GPU_MEMORY"
        echo "  • Tensor parallel size:   $TENSOR_PARALLEL"
        echo "  • Data type:             $DTYPE"
        [ -n "$QUANTIZATION" ] && echo "  • Quantization:          $QUANTIZATION"
        [ -n "$MAX_NUM_SEQS" ] && echo "  • Max sequences:         $MAX_NUM_SEQS"
        [ -n "$ENABLE_PREFIX_CACHE" ] && echo "  • Prefix caching:        $ENABLE_PREFIX_CACHE"
        
    else
        echo -e "${YELLOW}[!] Configuration file not found, using defaults${NC}"
        echo "    Expected: $CONFIG_PATH"
        echo ""
        echo -e "${BLUE}Creating default configuration...${NC}"
        
        # Create default config
        cat > "$CONFIG_PATH" <<EOF
# vLLM Configuration for $MODEL
# Generated: $(date)

max-model-len: 2048
gpu-memory-utilization: 0.9
tensor-parallel-size: 1
dtype: auto
EOF
        
        echo -e "${GREEN}[✓] Default configuration created${NC}"
        
        # Use defaults
        MAX_MODEL_LEN="2048"
        GPU_MEMORY="0.9"
        TENSOR_PARALLEL="1"
        DTYPE="auto"
        QUANTIZATION=""
    fi
    
    echo ""
    
    #############################################
    # Build vLLM Command
    #############################################
    
    echo -e "${BLUE}[*] Building vLLM command...${NC}"
    
    # Start with base command
    CMD="vllm serve \"$MODEL_PATH\""
    CMD="$CMD --port $CURRENT_PORT"
    CMD="$CMD --host 0.0.0.0"
    
    # Add configuration parameters
    CMD="$CMD --max-model-len $MAX_MODEL_LEN"
    CMD="$CMD --gpu-memory-utilization $GPU_MEMORY"
    CMD="$CMD --tensor-parallel-size $TENSOR_PARALLEL"
    CMD="$CMD --dtype $DTYPE"
    
    # Add optional parameters
    [ -n "$QUANTIZATION" ] && CMD="$CMD --quantization $QUANTIZATION"
    [ -n "$MAX_NUM_SEQS" ] && CMD="$CMD --max-num-seqs $MAX_NUM_SEQS"
    [ -n "$ENABLE_PREFIX_CACHE" ] && [ "$ENABLE_PREFIX_CACHE" = "true" ] && CMD="$CMD --enable-prefix-caching"
    
    echo -e "${GREEN}[✓] Command built${NC}"
    echo ""
    
    #############################################
    # Launch vLLM Server
    #############################################
    
    echo -e "${GREEN}[*] Starting vLLM server for $MODEL...${NC}"
    echo "    Port: $CURRENT_PORT"
    echo "    Path: $MODEL_PATH"
    echo ""
    
    # Launch in background with output prefix
    eval "$CMD" 2>&1 | sed "s/^/[$MODEL:$CURRENT_PORT] /" &
    VLLM_PID=$!
    PIDS+=($VLLM_PID)
    
    echo -e "${GREEN}[✓] Server started${NC}"
    echo "    PID: $VLLM_PID"
    echo "    Port: $CURRENT_PORT"
    echo ""
    
    MODEL_COUNT=$((MODEL_COUNT + 1))
    
    # Small delay to avoid startup conflicts
    sleep 2
done

#############################################
# Check Results
#############################################

echo -e "${CYAN}========================================${NC}"

if [ $MODEL_COUNT -eq 0 ]; then
    echo -e "${RED}ERROR: No Models Successfully Loaded${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
    echo -e "${YELLOW}Summary:${NC}"
    echo "  • Models in config: $(echo $MODEL_LIST | tr ',' '\n' | wc -l)"
    echo "  • Models loaded:    $MODEL_COUNT"
    echo "  • Models failed:    $FAILED_MODELS"
    echo ""
    echo "All configured models failed to load."
    echo ""
    echo -e "${GREEN}What to do:${NC}"
    echo ""
    echo "1. Check downloaded models:"
    echo -e "   ${BLUE}ls -la $MODEL_DIR/${NC}"
    echo ""
    echo "2. Download missing models:"
    echo -e "   ${BLUE}./pull_model.sh <model_name>${NC}"
    echo ""
    echo "3. Verify MODEL_LIST in .env matches actual models"
    echo ""
    echo "4. For help:"
    echo -e "   ${BLUE}./pull_model.sh${NC}  (shows available models)"
    echo ""
    exit 1
fi

#############################################
# Success - Server Running
#############################################

echo -e "${GREEN}✓ Successfully Started $MODEL_COUNT Model(s)${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

if [ $FAILED_MODELS -gt 0 ]; then
    echo -e "${YELLOW}Note: $FAILED_MODELS model(s) failed to load${NC}"
    echo ""
fi

echo -e "${GREEN}vLLM is now running! 🚀${NC}"
echo ""

#############################################
# Display Access Information
#############################################

echo -e "${CYAN}Access Your Models:${NC}"
echo "────────────────────────────────────────"

PORT_OFFSET=0
for entry in $(echo $MODEL_LIST | tr ',' '\n'); do
    MODEL=$(echo $entry | cut -d':' -f1)
    CURRENT_PORT=$((VLLM_PORT + PORT_OFFSET))
    
    # Check if this model was successfully loaded
    if [ -d "$MODEL_DIR/$MODEL" ]; then
        echo -e "  ${BLUE}$MODEL${NC}"
        echo "    http://localhost:$CURRENT_PORT"
        echo ""
    fi
    
    PORT_OFFSET=$((PORT_OFFSET + 1))
done

#############################################
# Display Test Commands
#############################################

echo -e "${CYAN}Test Commands:${NC}"
echo "────────────────────────────────────────"

# Get first successfully loaded model
FIRST_MODEL=$(echo $MODEL_LIST | cut -d',' -f1 | cut -d':' -f1)
FIRST_PORT=$VLLM_PORT

echo -e "${YELLOW}List models:${NC}"
echo -e "  ${BLUE}curl http://localhost:$FIRST_PORT/v1/models${NC}"
echo ""

echo -e "${YELLOW}Chat completion:${NC}"
cat <<EOF
  ${BLUE}curl -X POST http://localhost:$FIRST_PORT/v1/chat/completions \\
    -H "Content-Type: application/json" \\
    -d '{
      "model": "$FIRST_MODEL",
      "messages": [{"role": "user", "content": "Hello!"}],
      "max_tokens": 100
    }'${NC}
EOF

echo ""
echo ""

echo -e "${YELLOW}Streaming response:${NC}"
cat <<EOF
  ${BLUE}curl -X POST http://localhost:$FIRST_PORT/v1/chat/completions \\
    -H "Content-Type: application/json" \\
    -d '{
      "model": "$FIRST_MODEL",
      "messages": [{"role": "user", "content": "Count to 10"}],
      "stream": true
    }'${NC}
EOF

echo ""
echo ""

#############################################
# Display Control Information
#############################################

echo -e "${CYAN}────────────────────────────────────────${NC}"
echo -e "${YELLOW}To stop the server:${NC} Press Ctrl+C"
echo -e "${CYAN}────────────────────────────────────────${NC}"
echo ""
echo -e "${BLUE}Server logs will appear below:${NC}"
echo ""

#############################################
# Cleanup Handler
#############################################

cleanup() {
    echo ""
    echo ""
    echo -e "${YELLOW}[*] Shutting down vLLM servers...${NC}"
    
    for pid in "${PIDS[@]}"; do
        if kill -0 $pid 2>/dev/null; then
            echo "    • Stopping process $pid"
            kill -TERM $pid 2>/dev/null
        fi
    done
    
    # Wait a bit for graceful shutdown
    sleep 2
    
    # Force kill if still running
    for pid in "${PIDS[@]}"; do
        if kill -0 $pid 2>/dev/null; then
            echo "    • Force stopping process $pid"
            kill -9 $pid 2>/dev/null
        fi
    done
    
    echo -e "${GREEN}[✓] All servers stopped${NC}"
    echo ""
    exit 0
}

# Register cleanup handler
trap cleanup SIGINT SIGTERM

#############################################
# Wait for Processes
#############################################

# Wait for all background processes
wait
