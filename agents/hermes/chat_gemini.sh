#!/usr/bin/env bash
# Run Hermes with GEMINI as the LLM (instead of local qwen), for the qwen-vs-frontier experiment.
# Key lives OUTSIDE the repo at ~/.config/idlisseus/gemini.json {"api_key":"...","model":"gemini-2.5-flash"}.
# We DON'T touch the real config: we render a Gemini copy and mount it over /opt/data/config.yaml.
#
#   agents/hermes/chat_gemini.sh "is lantana spreading at the site?"   # one-shot
#   agents/hermes/chat_gemini.sh                                        # interactive
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SB="$(cd "$HERE/../../benchmarks/semantic_broker" && pwd)"
IMAGE="${HERMES_IMAGE:-hermes-agent-local}"
CREDS="$HOME/.config/idlisseus/gemini.json"
BASE="https://generativelanguage.googleapis.com/v1beta/openai"

[ -f "$CREDS" ] || { echo "No Gemini key at $CREDS (copy gemini.json.example, add your AI Studio key)."; exit 1; }
KEY="$(python3 -c "import json;print(json.load(open('$CREDS'))['api_key'])")"
MODEL="$(python3 -c "import json;print(json.load(open('$CREDS')).get('model','gemini-2.5-flash'))")"

# render a Gemini config from the real one (base_url + model + key swapped; provider stays 'custom').
# sed swaps existing values; awk INSERTS api_key into the top-level `model:` block (which has none).
TMP="$(mktemp /tmp/hermes_gemini_config.XXXX.yaml)"
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
