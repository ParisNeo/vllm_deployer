#!/bin/bash

#############################################
# vLLM Model Downloader and Configurator
# Downloads models from Hugging Face and
# automatically configures them for vLLM
#############################################

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Find the installation directory by looking for .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if .env exists in current directory or script directory
if [ -f ".env" ]; then
    ENV_FILE=".env"
    INSTALL_DIR="."
elif [ -f "$SCRIPT_DIR/.env" ]; then
    ENV_FILE="$SCRIPT_DIR/.env"
    INSTALL_DIR="$SCRIPT_DIR"
else
    ENV_FILE=""
    INSTALL_DIR="$SCRIPT_DIR"
fi

# Source .env if it exists to get MODEL_DIR
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
fi

MODEL_NAME="$1"
MODEL_DIR="${2:-${MODEL_DIR:-./models}}"

#############################################
# Help Text
#############################################

if [ -z "$MODEL_NAME" ]; then
    cat <<EOF
${CYAN}========================================${NC}
${CYAN}vLLM Model Installer${NC}
${CYAN}========================================${NC}

${YELLOW}Usage:${NC} $0 <model_name> [model_dir]

${YELLOW}Examples:${NC}
  $0 facebook/opt-125m
  $0 meta-llama/Llama-2-7b-chat-hf
  $0 mistralai/Mistral-7B-Instruct-v0.2

${CYAN}────────────────────────────────────────${NC}
${GREEN}Popular Models by Size${NC}
${CYAN}────────────────────────────────────────${NC}

${BLUE}Small Models (1-3B - Great for testing):${NC}
  ${GREEN}•${NC} facebook/opt-125m           ${YELLOW}125M params  ~250MB${NC}
    Fast testing, minimal GPU required
  
  ${GREEN}•${NC} facebook/opt-1.3b           ${YELLOW}1.3B params  ~2.5GB${NC}
    Good for development and testing
  
  ${GREEN}•${NC} microsoft/phi-2             ${YELLOW}2.7B params  ~5GB${NC}
    High quality small model
  
  ${GREEN}•${NC} stabilityai/stablelm-3b-4e1t ${YELLOW}3B params  ~6GB${NC}
    General purpose, efficient

${BLUE}Medium Models (7-13B - Production Ready):${NC}
  ${GREEN}•${NC} mistralai/Mistral-7B-Instruct-v0.2 ${YELLOW}7B params  ~14GB${NC}
    Excellent instruction following
  
  ${GREEN}•${NC} meta-llama/Llama-2-7b-chat-hf ${YELLOW}7B params  ~14GB${NC}
    Versatile conversational AI
  
  ${GREEN}•${NC} teknium/OpenHermes-2.5-Mistral-7B ${YELLOW}7B params  ~14GB${NC}
    Strong general assistant
  
  ${GREEN}•${NC} TheBloke/Llama-2-13B-chat-GPTQ ${YELLOW}13B params ~7GB${NC}
    13B quantized to 4-bit

${BLUE}Large Models (30B+ - High Performance):${NC}
  ${GREEN}•${NC} meta-llama/Llama-2-70b-chat-hf ${YELLOW}70B params  ~140GB${NC}
    Top-tier performance
  
  ${GREEN}•${NC} mistralai/Mixtral-8x7B-Instruct-v0.1 ${YELLOW}47B params  ~94GB${NC}
    Mixture of experts architecture

${CYAN}────────────────────────────────────────${NC}
${GREEN}Finding More Models${NC}
${CYAN}────────────────────────────────────────${NC}

${YELLOW}1. Browse Hugging Face Hub:${NC}
   https://huggingface.co/models
   
   Filter by:
   • Task: Text Generation
   • Library: transformers
   • Sort by: Most Downloads or Trending

${YELLOW}2. Check vLLM Compatibility:${NC}
   https://docs.vllm.ai/en/latest/models/supported_models.html
   
   Supported architectures:
   • LLaMA, LLaMA-2, LLaMA-3
   • Mistral, Mixtral
   • GPT-2, GPT-J, GPT-NeoX
   • OPT, BLOOM, Falcon
   • Qwen, Phi, Gemma, and more!

${YELLOW}3. Review Model Cards:${NC}
   • Check model size vs your GPU memory
   • Review license requirements
   • Read usage instructions

${CYAN}────────────────────────────────────────${NC}
${GREEN}GPU Memory Requirements (FP16)${NC}
${CYAN}────────────────────────────────────────${NC}

  ${YELLOW}1B parameters${NC}  ≈ 2GB VRAM
  ${YELLOW}7B parameters${NC}  ≈ 14GB VRAM
  ${YELLOW}13B parameters${NC} ≈ 26GB VRAM
  ${YELLOW}70B parameters${NC} ≈ 140GB VRAM

${BLUE}💡 Tips:${NC}
  • Use quantized models (GPTQ, AWQ) for less memory
  • Quantized models use ~4-bit precision (~75% less memory)
  • Start with smaller models for testing
  • Check model README for specific requirements

${CYAN}────────────────────────────────────────${NC}
${GREEN}Protected/Gated Models${NC}
${CYAN}────────────────────────────────────────${NC}

Some models (like official LLaMA) require authentication:

  ${BLUE}huggingface-cli login${NC}
  
Then download:
  ${BLUE}./pull_model.sh meta-llama/Llama-2-7b-chat-hf${NC}

Get token: https://huggingface.co/settings/tokens

${CYAN}========================================${NC}
EOF
    exit 1
fi

#############################################
# Start Download Process
#############################################

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}vLLM Model Downloader${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${BLUE}Model:${NC} $MODEL_NAME"
echo -e "${BLUE}Destination:${NC} $MODEL_DIR"
echo ""

# Extract just the model name for the folder
MODEL_FOLDER_NAME=$(echo "$MODEL_NAME" | sed 's|.*/||')
FULL_MODEL_PATH="$MODEL_DIR/$MODEL_FOLDER_NAME"

# Check if model already exists
if [ -d "$FULL_MODEL_PATH" ] && [ "$(ls -A $FULL_MODEL_PATH)" ]; then
    echo -e "${YELLOW}[!] Model directory already exists: $FULL_MODEL_PATH${NC}"
    read -p "$(echo -e ${YELLOW}Overwrite? [y/N]:${NC} )" -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Download cancelled."
        exit 0
    fi
    rm -rf "$FULL_MODEL_PATH"
fi

mkdir -p "$FULL_MODEL_PATH"

echo -e "${BLUE}[1/4] Checking dependencies...${NC}"
echo ""

# Check for huggingface-cli
if ! command -v huggingface-cli &> /dev/null; then
    echo -e "${YELLOW}[*] huggingface-cli not found. Installing...${NC}"
    pip install huggingface-hub
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[✓] huggingface-hub installed${NC}"
    else
        echo -e "${RED}[✗] Failed to install huggingface-hub${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}[✓] huggingface-cli is available${NC}"
fi

echo ""
echo -e "${BLUE}[2/4] Downloading model from Hugging Face...${NC}"
echo -e "${YELLOW}This may take several minutes depending on model size...${NC}"
echo ""

# Download the model
huggingface-cli download "$MODEL_NAME" --local-dir "$FULL_MODEL_PATH" --local-dir-use-symlinks False

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}Download Failed${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${YELLOW}Possible reasons:${NC}"
    echo "  • Model name is incorrect"
    echo "  • Model requires authentication"
    echo "  • Network connectivity issues"
    echo "  • Insufficient disk space"
    echo ""
    echo -e "${GREEN}If this is a gated model:${NC}"
    echo "  1. Get a token from: https://huggingface.co/settings/tokens"
    echo "  2. Login: huggingface-cli login"
    echo "  3. Try again: $0 $MODEL_NAME"
    echo ""
    exit 1
fi

echo ""
echo -e "${GREEN}[✓] Model downloaded successfully!${NC}"
echo ""

#############################################
# Create YAML Configuration
#############################################

echo -e "${BLUE}[3/4] Creating vLLM configuration...${NC}"
echo ""

CONFIG_FILE="$FULL_MODEL_PATH/vllm_config.yaml"

cat > "$CONFIG_FILE" <<EOF
# vLLM Configuration for $MODEL_FOLDER_NAME
# Generated: $(date)
# Documentation: https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html

# Maximum sequence length (context window)
# Adjust based on model capabilities and available memory
max-model-len: 2048

# GPU memory utilization (0.0 - 1.0)
# 0.9 = use 90% of GPU memory for model
# Lower this if you get OOM errors
gpu-memory-utilization: 0.9

# Number of GPUs for tensor parallelism
# Set to 1 for single GPU
# Set to 2, 4, or 8 for multi-GPU setups
tensor-parallel-size: 1

# Data type for model weights
# Options: auto, float16, bfloat16, float32
# auto = let vLLM decide (recommended)
dtype: auto

# Quantization method (uncomment if using quantized models)
# Options: awq, gptq, squeezellm
# quantization: gptq

# Additional options (uncomment to use):
# max-num-seqs: 256              # Maximum number of sequences per batch
# max-num-batched-tokens: 8192   # Maximum tokens per batch
# enable-prefix-caching: true    # Enable KV cache for common prefixes
# disable-log-stats: false       # Disable logging statistics
EOF

echo -e "${GREEN}[✓] Configuration file created: vllm_config.yaml${NC}"
echo ""

#############################################
# Update .env File
#############################################

echo -e "${BLUE}[4/4] Updating configuration...${NC}"
echo ""

if [ -f "$ENV_FILE" ]; then
    # Read current MODEL_LIST value
    CURRENT_MODEL_LIST=$(grep "^MODEL_LIST=" "$ENV_FILE" | cut -d'=' -f2- | tr -d "'\"")
    
    # New model entry
    NEW_ENTRY="${MODEL_FOLDER_NAME}:vllm_config.yaml"
    
    # Check if model already exists in the list
    if echo "$CURRENT_MODEL_LIST" | grep -q "$MODEL_FOLDER_NAME"; then
        echo -e "${YELLOW}[!] Model $MODEL_FOLDER_NAME already exists in MODEL_LIST${NC}"
        echo -e "${BLUE}[*] Skipping .env update${NC}"
    else
        # Add to existing list (with comma if list is not empty)
        if [ -z "$CURRENT_MODEL_LIST" ]; then
            NEW_MODEL_LIST="$NEW_ENTRY"
        else
            NEW_MODEL_LIST="${CURRENT_MODEL_LIST},${NEW_ENTRY}"
        fi
        
        # Create backup
        cp "$ENV_FILE" "${ENV_FILE}.bak"
        
        # Update the .env file
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s|^MODEL_LIST=.*|MODEL_LIST='${NEW_MODEL_LIST}'|" "$ENV_FILE"
        else
            # Linux
            sed -i "s|^MODEL_LIST=.*|MODEL_LIST='${NEW_MODEL_LIST}'|" "$ENV_FILE"
        fi
        
        echo -e "${GREEN}[✓] Model added to .env configuration${NC}"
        echo -e "${BLUE}[*] Updated MODEL_LIST:${NC}"
        echo "    $NEW_MODEL_LIST"
        echo -e "${BLUE}[*] Backup saved:${NC} ${ENV_FILE}.bak"
    fi
else
    echo -e "${YELLOW}[!] WARNING: .env file not found${NC}"
    echo ""
    echo -e "${BLUE}Expected location:${NC} $INSTALL_DIR/.env"
    echo ""
    echo -e "${YELLOW}Manual configuration required:${NC}"
    echo "  Add to .env file:"
    echo "  MODEL_LIST='$MODEL_FOLDER_NAME:vllm_config.yaml'"
fi

#############################################
# Summary and Next Steps
#############################################

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Get model size
MODEL_SIZE=$(du -sh "$FULL_MODEL_PATH" 2>/dev/null | cut -f1)

echo -e "${BLUE}Model Information:${NC}"
echo "  Name:     $MODEL_FOLDER_NAME"
echo "  Path:     $FULL_MODEL_PATH"
echo "  Size:     ${MODEL_SIZE:-Unknown}"
echo "  Config:   vllm_config.yaml"
echo ""

if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}✓ Model automatically configured in .env${NC}"
    echo ""
    echo -e "${CYAN}Next Steps:${NC}"
    echo ""
    echo -e "${YELLOW}Option 1: Start with run.sh${NC}"
    echo "  ${BLUE}./run.sh${NC}"
    echo ""
    echo -e "${YELLOW}Option 2: Use management interface${NC}"
    echo "  ${BLUE}./start_manager.sh${NC}"
    echo "  Then in another terminal:"
    echo "  ${BLUE}curl -X POST http://localhost:9000/models/$MODEL_FOLDER_NAME/start${NC}"
    echo ""
    echo -e "${YELLOW}Option 3: Install as service${NC}"
    echo "  ${BLUE}./manage_service.sh install${NC}"
    echo "  ${BLUE}systemctl start vllm${NC}"
else
    echo -e "${YELLOW}Manual Configuration Required:${NC}"
    echo ""
    echo "1. Create or locate your .env file"
    echo ""
    echo "2. Add this line to .env:"
    echo "   ${BLUE}MODEL_LIST='$MODEL_FOLDER_NAME:vllm_config.yaml'${NC}"
    echo ""
    echo "3. Start the server:"
    echo "   ${BLUE}./run.sh${NC}"
fi

echo ""
echo -e "${CYAN}Configuration Tips:${NC}"
echo "  • Edit config: ${BLUE}nano $CONFIG_FILE${NC}"
echo "  • Adjust max-model-len for longer contexts"
echo "  • Lower gpu-memory-utilization if OOM errors occur"
echo "  • Set tensor-parallel-size for multi-GPU setups"
echo ""

echo -e "${CYAN}Test Your Model:${NC}"
echo "  ${BLUE}curl http://localhost:8000/v1/models${NC}"
echo "  ${BLUE}curl -X POST http://localhost:8000/v1/chat/completions \\${NC}"
echo "    ${BLUE}-H \"Content-Type: application/json\" \\${NC}"
echo "    ${BLUE}-d '{${NC}"
echo "      ${BLUE}\"model\": \"$MODEL_FOLDER_NAME\",${NC}"
echo "      ${BLUE}\"messages\": [{\"role\": \"user\", \"content\": \"Hello!\"}]${NC}"
echo "    ${BLUE}}'${NC}"
echo ""

echo -e "${CYAN}Documentation:${NC}"
echo "  • vLLM docs:  https://docs.vllm.ai"
echo "  • Model card: https://huggingface.co/$MODEL_NAME"
echo "  • README:     cat README.md"
echo ""

echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}Happy Serving! 🚀${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
