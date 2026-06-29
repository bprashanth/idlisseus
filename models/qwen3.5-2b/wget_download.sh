#!/bin/bash
# Download Qwen/Qwen3.5-2B via wget -c directly to HF blob cache.
# Bypasses hf_transfer and huggingface-hub CLI which both stall on this network.
#
# After the blob is downloaded, run once:
#   HF_HUB_ENABLE_HF_TRANSFER=0 hf download Qwen/Qwen3.5-2B
# to create the snapshot symlinks (skips the already-present blob).
#
# Model: single shard (model.safetensors-00001-of-00001.safetensors), 4.23GB BF16 (4,548,221,488 bytes)
# Blob hash: aa33250c4fc64891ddfaba3a314fd9542ea371843c387178b425fbcc5ed680b1

set -euo pipefail

BLOB_DIR="$HOME/.cache/huggingface/hub/models--Qwen--Qwen3.5-2B/blobs"
HASH="aa33250c4fc64891ddfaba3a314fd9542ea371843c387178b425fbcc5ed680b1"
DEST="$BLOB_DIR/$HASH"
URL="https://huggingface.co/Qwen/Qwen3.5-2B/resolve/main/model.safetensors-00001-of-00001.safetensors"

rm -f "$BLOB_DIR"/*.incomplete

if [ -f "$DEST" ]; then
  echo "Resuming from $(stat -c%s "$DEST") bytes..."
fi

wget -c "$URL" -O "$DEST" --progress=dot:giga 2>&1

echo "Download complete: $(ls -lh "$DEST")"
echo "Creating HF cache symlinks..."
export PATH="$HOME/.local/bin:$PATH"
HF_HUB_ENABLE_HF_TRANSFER=0 hf download Qwen/Qwen3.5-2B 2>&1 | grep -v "Warning:"
echo "Done. Test: curl -s http://172.17.0.1:8001/v1/models  (start sidekick first)"
