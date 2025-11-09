Here are the updated files with better guidance for finding and installing models:

---

### pull_model.sh (enhanced with examples and instructions)

```bash
#!/bin/bash

# Usage: ./pull_model.sh model_name [model_dir]
MODEL_NAME="$1"
MODEL_DIR="${2:-./models}"

if [ -z "$MODEL_NAME" ]; then
    cat <<EOF
========================================
vLLM Model Installer
========================================

Usage: $0 <model_name> [model_dir]

Examples:
  $0 facebook/opt-125m
  $0 meta-llama/Llama-2-7b-chat-hf
  $0 mistralai/Mistral-7B-Instruct-v0.2

Popular Models by Size:
----------------------------------------
Small (1-3B - Great for testing):
  • facebook/opt-125m           (125M params, ~250MB)
  • facebook/opt-1.3b           (1.3B params, ~2.5GB)
  • microsoft/phi-2             (2.7B params, ~5GB)
  • stabilityai/stablelm-3b-4e1t (3B params, ~6GB)

Medium (7-13B - Good balance):
  • meta-llama/Llama-2-7b-chat-hf      (7B params, ~14GB)
  • mistralai/Mistral-7B-Instruct-v0.2 (7B params, ~14GB)
  • teknium/OpenHermes-2.5-Mistral-7B  (7B params, ~14GB)
  • TheBloke/Llama-2-13B-chat-GPTQ     (13B params, ~7GB quantized)

Large (30B+ - Requires significant GPU):
  • meta-llama/Llama-2-70b-chat-hf     (70B params, ~140GB)
  • mistralai/Mixtral-8x7B-Instruct-v0.1 (47B params, ~94GB)

Finding Models:
----------------------------------------
1. Browse Hugging Face: https://huggingface.co/models
2. Filter by:
   - Task: Text Generation
   - Library: transformers
   - Sort by: Most Downloads or Trending
3. Check model card for:
   - Model size vs your GPU memory
   - License requirements
   - Supported architectures

Supported Architectures:
----------------------------------------
vLLM supports many architectures including:
  • LLaMA, LLaMA-2, LLaMA-3
  • Mistral, Mixtral
  • GPT-2, GPT-J, GPT-NeoX
  • OPT, BLOOM
  • Falcon, Qwen, Phi
  • And many more!

Full list: https://docs.vllm.ai/en/latest/models/supported_models.html

GPU Memory Requirements:
----------------------------------------
Rough estimates (FP16):
  • 1B params  ≈ 2GB VRAM
  • 7B params  ≈ 14GB VRAM
  • 13B params ≈ 26GB VRAM
  • 70B params ≈ 140GB VRAM

Tips:
  • Use quantized models (GPTQ, AWQ) for less memory
  • Start with smaller models for testing
  • Check model README for requirements

========================================
EOF
    exit 1
fi

echo "========================================="
echo "Downloading model: $MODEL_NAME"
echo "========================================="

# Extract just the model name for the folder
MODEL_FOLDER_NAME=$(echo "$MODEL_NAME" | sed 's|.*/||')
FULL_MODEL_PATH="$MODEL_DIR/$MODEL_FOLDER_NAME"

mkdir -p "$FULL_MODEL_PATH"

echo "[*] Target directory: $FULL_MODEL_PATH"
echo "[*] Checking if huggingface-cli is available..."

if ! command -v huggingface-cli &> /dev/null; then
    echo "[!] huggingface-cli not found. Installing huggingface-hub..."
    pip install huggingface-hub
fi

echo "[*] Downloading model from Hugging Face..."
echo "    This may take a while depending on model size..."

# Download the model
huggingface-cli download "$MODEL_NAME" --local-dir "$FULL_MODEL_PATH" --local-dir-use-symlinks False

if [ $? -ne 0 ]; then
    echo "[!] ERROR: Failed to download model"
    echo "[!] Possible reasons:"
    echo "    - Model name is incorrect"
    echo "    - Model requires authentication (use: huggingface-cli login)"
    echo "    - Network connectivity issues"
    exit 1
fi

echo "[*] Model downloaded successfully!"
echo ""

# Generate a basic default config file for vLLM usage
CONFIG_FILE="$FULL_MODEL_PATH/vllm_config.json"
echo "[*] Creating default vLLM configuration: $CONFIG_FILE"

cat > "$CONFIG_FILE" <<EOF
{
  "max_model_len": 2048,
  "gpu_memory_utilization": 0.9,
  "tensor_parallel_size": 1,
  "dtype": "auto",
  "quantization": null
}
EOF

echo "[*] Configuration file created with default settings."
echo ""
echo "========================================="
echo "✓ Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Edit your .env file:"
echo "     nano .env"
echo ""
echo "  2. Add this model to MODEL_LIST:"
echo "     MODEL_LIST='$MODEL_FOLDER_NAME:vllm_config.json'"
echo ""
echo "  3. If you have multiple models, use comma separation:"
echo "     MODEL_LIST='model1:vllm_config.json,model2:vllm_config.json'"
echo ""
echo "  4. Adjust vllm_config.json if needed:"
echo "     nano $CONFIG_FILE"
echo ""
echo "  5. Test the setup:"
echo "     ./run.sh"
echo ""
echo "Model location: $FULL_MODEL_PATH"
echo "========================================="
```

***

### README.md (add new comprehensive section before "Quick Start")

Add this section after the "Requirements" section:

```markdown
