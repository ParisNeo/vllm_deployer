#!/bin/bash
set -a
source "$(dirname "$0")/.env"
set +a

for entry in $(echo $MODEL_LIST | tr ',' '\n'); do
    MODEL=$(echo $entry | cut -d':' -f1)
    CONFIG=$(echo $entry | cut -d':' -f2)
    vllm serve --model "$MODEL_DIR/$MODEL" --config "$MODEL_DIR/$CONFIG" --port ${VLLM_PORT} &
done
wait
