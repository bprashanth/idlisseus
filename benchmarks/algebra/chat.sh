#!/usr/bin/env bash
# Conversational Hermes with the conservation connectors + 122B already wired in.
# Users just ask naturally — "use the connectors" is baked into ~/.hermes/SOUL.md,
# so you never have to say it. Connectors mounted, Earth Engine ready, 122B backing.
#
#   ./chat.sh                            # interactive conversation (Ctrl-D / 'exit' to quit)
#   ./chat.sh "is lantana spreading at the site?"   # one-shot question
#   SESSION=mythread ./chat.sh "..."     # use / continue a named conversation thread
#
# Notes: needs 122B up (docker start vllm-qwen35) and the hermes-agent-local image.
# A turn takes ~1-15 min (it runs real Earth Engine analysis). Transcript persists in
# the session, so follow-up questions keep context.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SB="$(cd "$HERE/../semantic_broker" && pwd)"
IMAGE="${HERMES_IMAGE:-hermes-agent-local}"
SESSION="${SESSION:-conservation}"

MOUNTS=(--network host
  -v "$HOME/.hermes:/opt/data"
  -v "$SB/connectors:/opt/data/connectors:ro"
  -v "$SB/queries/data:/opt/data/query_data:ro"
  -e HOME=/opt/data)

if [ "$#" -gt 0 ]; then
  # one-shot. CONTINUE=1 continues the latest session (memory across separate calls).
  if [ "${CONTINUE:-0}" = "1" ]; then
    docker run --rm "${MOUNTS[@]}" "$IMAGE" chat -c -q "$*"
  else
    docker run --rm "${MOUNTS[@]}" "$IMAGE" chat -q "$*"
  fi
else
  # interactive REPL — this single session IS the conversation (keeps full context).
  docker run --rm -it "${MOUNTS[@]}" "$IMAGE" chat
fi
