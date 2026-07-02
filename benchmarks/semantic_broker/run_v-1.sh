#!/usr/bin/env bash
# v-1 "Hermes runs wild" runner.
# Hands Hermes (122B) the raw corpus + live connectors (Earth Engine etc.) and
# ONE benchmark question. No broker, no cards, no embeddings. See EXPERIMENT_v-1.md.
#
# No-coercion rule: the prompt names the available connectors (that's the tool
# list) but never says which /corpus file or which layer answers the question.
#
# Preconditions (one-time):
#   1. Model pointed at 122B (already is: `qwen` @ 172.17.0.1:8001).
#   2. Image built WITH ee/pymupdf preinstalled + ENV HOME=/opt/data:
#        bash agents/hermes/build.sh   (-> hermes-agent-local)
#   3. EE creds staged at the *sandbox* HOME. execute_code sandboxes run with
#      HOME={HERMES_HOME}/home = /opt/data/home (Hermes' container HOME contract),
#      so creds must live there, NOT at /opt/data/.config:
#        sudo mkdir -p ~/.hermes/home/.config/earthengine
#        sudo cp ~/.config/earthengine/credentials ~/.hermes/home/.config/earthengine/credentials
#        sudo chown -R 10000:10000 ~/.hermes/home
#   4. ~/.hermes itself must be owned by uid 10000 (container user), else the
#      agent can't cd into /opt/data:  sudo chown -R 10000:10000 ~/.hermes
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
CORPUS="$REPO/benchmarks/semantic_broker/assets"
QUESTION="${1:?usage: run_v-1.sh \"<benchmark question>\"}"
IMAGE="${HERMES_IMAGE:-hermes-agent-local}"

# Connectors advertised to Hermes (the "tool list"). Distractor connectors are
# included on purpose to see whether it wastes time on the wrong ones.
PROMPT="Your working directory is /opt/data. Raw datasets and research papers are in \
/opt/data/corpus/ (subdirectories) — that is the ONLY corpus location; ignore any other \
leftover folders in /opt/data. \
You also have Earth Engine in Python (import ee; ee.Initialize(project='plantwars')) for \
map layers — active fire (FIRMS), 10m land cover (ESA/WorldCover/v200), terrain \
(USGS/SRTMGL1_003), protected-area boundaries (WCMC/WDPA/current/polygons) — and the public \
GBIF occurrence API (api.gbif.org) for species records. Other layers exist too (e.g. ocean \
SST, air quality) if relevant. \
Using whatever of these is appropriate, answer this question: ${QUESTION} \
Report exactly which /corpus files and which connectors/layers you used, and show your work."

# HOME=/opt/data  -> ee finds creds at /opt/data/.config/earthengine/credentials
# UV_* -> container-local package cache (host mount root is not agent-writable;
#         this is the fix for the pymupdf 'failed to create directory' failure).
exec docker run --rm --network host \
  -v "$HOME/.hermes:/opt/data" \
  -v "$CORPUS:/opt/data/corpus:ro" \
  -e HOME=/opt/data \
  -e UV_CACHE_DIR=/tmp/uv-cache \
  -e UV_PYTHON_INSTALL_DIR=/tmp/uv-py \
  -e UV_PYTHON_DOWNLOADS=never \
  "$IMAGE" chat -q "$PROMPT"
