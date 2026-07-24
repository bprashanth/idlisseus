#!/usr/bin/env bash
# Run Hermes with an OPENROUTER open-weight model as the LLM (instead of local qwen),
# for the "122B-on-my-DGX vs a bigger open model on a future cluster" ROI experiment.
#
# Key lives OUTSIDE the repo at ~/.config/idlisseus/openrouter.json:
#     {"api_key":"sk-or-v1-...","model":"deepseek/deepseek-v4-flash"}
# Get the key at https://openrouter.ai/keys ; copy exact model slugs from
# https://openrouter.ai/models (must support tool-calling for Hermes's agent loop).
#
# We DON'T touch the real config: we render an OpenRouter copy and mount it over
# /opt/data/config.yaml (same trick as chat_gemini.sh).
#
#   agents/hermes/chat_openrouter.sh "is lantana spreading at the site?"                # one-shot, default model
#   agents/hermes/chat_openrouter.sh --model z-ai/glm-5.2 "which natives to plant?"     # override model
#   agents/hermes/chat_openrouter.sh                                                     # interactive
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SB="$(cd "$HERE/../../benchmarks/semantic_broker" && pwd)"
IMAGE="${HERMES_IMAGE:-hermes-agent-local}"
CREDS="$HOME/.config/idlisseus/openrouter.json"
BASE="https://openrouter.ai/api/v1"

[ -f "$CREDS" ] || { echo "No OpenRouter key at $CREDS (copy openrouter.json.example, add your key)."; exit 1; }
KEY="$(python3 -c "import json;print(json.load(open('$CREDS'))['api_key'])")"
MODEL="$(python3 -c "import json;print(json.load(open('$CREDS')).get('model','deepseek/deepseek-v4-flash'))")"

# optional --model override
if [ "${1:-}" = "--model" ]; then MODEL="$2"; shift 2; fi

# render an OpenRouter config from the real one (base_url + model + key swapped; provider stays 'custom').
# sed swaps existing values; awk INSERTS api_key into the top-level `model:` block (which has none).
TMP="$(mktemp /tmp/hermes_openrouter_config.XXXX.yaml)"
sudo cat "$HOME/.hermes/config.yaml" | sed \
  -e "s|http://172.17.0.1:8001/v1|$BASE|g" \
  -e "s|default: qwen|default: $MODEL|g" \
  -e "s|model: qwen|model: $MODEL|g" \
  -e "s|api_key: ''|api_key: '$KEY'|g" \
| awk -v key="$KEY" '
    /^model:/{inm=1}
    inm && /^  base_url:/{print; print "  api_key: '\''" key "'\''"; inm=0; next}
    {print}' > "$TMP"
chmod 644 "$TMP"   # the Hermes container runs as uid 10000 and must be able to READ it
trap 'rm -f "$TMP"' EXIT

echo "[chat_openrouter] model=$MODEL" >&2
MOUNTS=(--network host
  -v "$HOME/.hermes:/opt/data"
  -v "$TMP:/opt/data/config.yaml:ro"
  -v "$SB/connectors:/opt/data/connectors:ro"
  -v "$SB/queries/data:/opt/data/query_data:ro"
  -e HOME=/opt/data)

if [ "$#" -gt 0 ]; then
  docker run --rm "${MOUNTS[@]}" "$IMAGE" chat -q "$*"
else
  docker run --rm -it "${MOUNTS[@]}" "$IMAGE" chat
fi
