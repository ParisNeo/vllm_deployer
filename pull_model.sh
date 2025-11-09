#!/bin/bash

# Usage: ./pull_model.sh model_name [model_dir]
MODEL_NAME="$1"
MODEL_DIR="${2:-./models}"

if [ -z "$MODEL_NAME" ]; then
    echo "Usage: $0 model_name [model_dir]"
    exit 1
fi

mkdir -p "$MODEL_DIR/$MODEL_NAME"

echo "Pulling Hugging Face model '$MODEL_NAME' into $MODEL_DIR/$MODEL_NAME ..."
huggingface-cli repo clone "$MODEL_NAME" "$MODEL_DIR/$MODEL_NAME"

echo '{
  "max_seq_len": 2048,
  "tensor_parallel_size": 1,
  "offload": false,
  "quantization": null
}' > "$MODEL_DIR/$MODEL_NAME/vllm_config.json"

echo "Model $MODEL_NAME pulled and configuration file vllm_config.json created."
echo "Update your .env MODEL_LIST with '$MODEL_NAME:vllm_config.json'"
