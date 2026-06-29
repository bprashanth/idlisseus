#!/bin/bash
# Download Qwen3-Next-80B-A3B-Instruct-FP8 via wget -c directly to HF blob cache.
# This bypasses hf_transfer's parallel multi-connection downloader, which stalls
# on this network (CDN connections go idle mid-download, 2-3 stalls per attempt).
#
# wget -c streams sequentially to disk with reliable byte-range resume on restart.
# Run this with ds4 STOPPED to free ~93GB of unified memory.
#
# After all shards complete, run:
#   HF_HUB_ENABLE_HF_TRANSFER=0 hf download Qwen/Qwen3-Next-80B-A3B-Instruct-FP8
# to create the snapshot symlinks (it'll see all blobs as present, skip downloads).
#
# Shard mapping (from HF API /tree endpoint, blob hash = LFS SHA256):
# a0252e2f...  model-00001-of-00008.safetensors  10.7GB
# 183594483b.. model-00002-of-00008.safetensors  10.7GB
# 08a8d3bf...  model-00003-of-00008.safetensors  10.7GB
# 36dd5766...  model-00004-of-00008.safetensors  10.7GB
# 4533fccdd4.. model-00005-of-00008.safetensors  10.7GB
# 13da74e9...  model-00006-of-00008.safetensors  10.7GB
# a3e5a698...  model-00007-of-00008.safetensors  10.7GB
# a2c110f8...  model-00008-of-00008.safetensors   6.9GB

set -euo pipefail

BLOB_DIR="$HOME/.cache/huggingface/hub/models--Qwen--Qwen3-Next-80B-A3B-Instruct-FP8/blobs"
BASE_URL="https://huggingface.co/Qwen/Qwen3-Next-80B-A3B-Instruct-FP8/resolve/main"

# Remove any stale .incomplete files from prior hf_transfer runs (NOT safe to resume
# those — hf_transfer writes chunks at arbitrary offsets so partial files may have gaps)
echo "Cleaning stale .incomplete files..."
rm -f "$BLOB_DIR"/*.incomplete

declare -A SHARDS=(
  ["model-00001-of-00008.safetensors"]="a0252e2f8efae97757d6dfd1b0a8e2f9bcb24802a515379bd9845f42c3f9f9fa"
  ["model-00002-of-00008.safetensors"]="183594483ba1101d2a5450188046a30bb9d430722c69e5455e10d141e6f935ed"
  ["model-00003-of-00008.safetensors"]="08a8d3bf27fc90fb3520bc916f7eafeeaf15533a472b6b884293a0f09438a874"
  ["model-00004-of-00008.safetensors"]="36dd5766db329b672ac535dbafdb7247a6c47a1cafeb08b5b3f1a7511568a04e"
  ["model-00005-of-00008.safetensors"]="4533fccdd49dd9032f80f5ea3b0f8566cfe8694444e7923361244f26a0fe0ec1"
  ["model-00006-of-00008.safetensors"]="13da74e9313b460799ac6ce682915e82913b6ee349d84494358d93815a1fcffc"
  ["model-00007-of-00008.safetensors"]="a3e5a69858e5c15938cfe13326b942e09ad50799d299ac2332ce76d01b89894c"
  ["model-00008-of-00008.safetensors"]="a2c110f8e7cee640817023fa07c9d19051d93a777c166e6a611725cf3b9d1b7b"
)

echo "Starting sequential shard downloads (wget -c for reliable resume)..."
echo "Monitor progress: watch -n10 'ls -lh $BLOB_DIR/*.safetensors 2>/dev/null'"

for SHARD in $(echo "${!SHARDS[@]}" | tr ' ' '\n' | sort); do
  HASH="${SHARDS[$SHARD]}"
  DEST="$BLOB_DIR/$HASH"
  URL="$BASE_URL/$SHARD"

  if [ -f "$DEST" ]; then
    ACTUAL=$(stat -c%s "$DEST")
    echo "[$SHARD] already at $ACTUAL bytes — verifying completeness via wget -c"
  else
    echo "[$SHARD] starting fresh download -> $HASH"
  fi

  wget -c "$URL" -O "$DEST" --progress=dot:giga 2>&1
  echo "[$SHARD] DONE: $(ls -lh "$DEST")"
done

echo ""
echo "All shards complete. Creating HF cache symlinks..."
export PATH="$HOME/.local/bin:$PATH"
HF_HUB_ENABLE_HF_TRANSFER=0 hf download Qwen/Qwen3-Next-80B-A3B-Instruct-FP8 2>&1 | grep -v "Warning:"
echo "Done. Test with: curl -s http://172.17.0.1:8000/v1/models"
