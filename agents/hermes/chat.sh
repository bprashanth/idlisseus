#!/usr/bin/env bash
# chat.sh — talk to the Hermes conservation agent via a PERSISTENT container (fast; no per-query startup).
#
#   chat.sh                              interactive on the local 122B (just enter hermes)
#   chat.sh "is lantana spreading?"      one-shot
#   chat.sh --model deepseekv4 "..."     one-shot on DeepSeek-V4  (or glm5.2, or a raw provider/slug)
#   chat.sh --restart                    recreate the container (after a config.yaml or image change)
#
# DETERMINISM: the model is chosen by the --model flag on EACH call and passed explicitly to hermes
# (-m … --provider …); it does NOT depend on config.yaml's default or on any prior in-session /model
# switch, and every call is a fresh session (set CONTINUE=1 to resume). So `chat.sh` = local qwen and
# `chat.sh --model deepseekv4` = DeepSeek, every time — no container restart needed to switch models.
# (First call on a cold model is slower; the persistent container only saves process/venv startup.)
# The local qwen is registered in config.yaml as providers.local (routed via `--provider custom`).
# Connectors + PLAYBOOK.md are LIVE-mounted → edits take effect on the next call, NO restart.
# Only a config.yaml/image/key change needs --restart.
set -uo pipefail

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  cat <<'HELP'
chat.sh — Hermes conservation agent (persistent container; connectors + Earth Engine + DSS skills).

USAGE
  chat.sh [--model M] [QUESTION]        interactive (no QUESTION) or one-shot
  chat.sh --restart                     recreate the container (after a config.yaml / image / key change)

MODEL (default = local 122B / qwen)
  --model qwen122b      local Qwen3.5-122B (free)
  --model deepseekv4    DeepSeek-V4-Flash via OpenRouter (fast, cheap)
  --model glm5.2        GLM-5.2 via OpenRouter (reasoning, thorough)
  --model <prov/slug>   any OpenRouter slug (routed via OPENROUTER_API_KEY)

ASSEMBLED MODE ("smart bookends, cheap middle")
  --smart-model M   enable the 3-stage loop: clarify-gate (smart) → cheap runner → synthesizer (smart)
  --cheap-model M   the runner that executes connectors (defaults qwen122b)
  Both default to qwen122b if unset; absent both flags, chat.sh runs the normal single-model path.
  e.g.  chat.sh --smart-model glm5.2 --cheap-model qwen122b        (interactive)
        chat.sh --smart-model glm5.2 "tell me about the invasives here"

IN-SESSION (interactive)
  /model z-ai/glm-5.2 --provider openrouter     switch to GLM live
  /model deepseek/deepseek-v4-flash --provider openrouter
  /model qwen --provider custom                 back to local 122B
  /why      /help      /reset

ENV
  AUTO_APPROVE=1   pass --yolo (skip the approval gate — recommended for non-interactive)
  CONTINUE=1       continue the latest session

NOTES
  Connectors + PLAYBOOK.md are live-mounted — edit them and the next call picks it up (no restart).
  OpenRouter key: ~/.config/idlisseus/openrouter.json
HELP
  exit 0
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
DSS="$(cd "$HERE/../../dss" && pwd)"   # capability library moved out of benchmarks/ (2026-07-11)
IMAGE="${HERMES_IMAGE:-hermes-agent-local}"
NAME="${HERMES_CONTAINER:-hermes-live}"
CREDS="$HOME/.config/idlisseus/openrouter.json"

start_container() {
  docker rm -f "$NAME" >/dev/null 2>&1
  local key=""
  [ -f "$CREDS" ] && key="$(python3 -c "import json;print(json.load(open('$CREDS'))['api_key'])" 2>/dev/null)"
  mkdir -p "$HERE/gt"; chmod 777 "$HERE/gt" 2>/dev/null || true
  docker run -d --name "$NAME" --network host -e HOME=/opt/data \
    ${key:+-e OPENROUTER_API_KEY="$key"} \
    -v "$HOME/.hermes:/opt/data" \
    -v "$DSS/connectors:/opt/data/connectors:ro" \
    -v "$DSS/queries/data:/opt/data/query_data:ro" \
    -v "$DSS/corpus:/opt/data/corpus:ro" \
    -v "$HERE/gt:/opt/data/work/gt" \
    --entrypoint /opt/hermes/.venv/bin/python3 "$IMAGE" -c "import time; time.sleep(1e9)" >/dev/null
  sleep 2
  # Stage login-connector keys (ebird/dryad/skyfi) so the in-container connectors find them. They check
  # ~/.config/idlisseus/*.json, which inside the container (HOME=/opt/data) is /opt/data/.config/idlisseus.
  # The host source ~/.config/idlisseus is NOT reachable from the container, and ~/.hermes is owned by the
  # agent uid (10000) so a host-side cp is denied — copy via docker + fix ownership. Durable via the mount.
  if [ -d "$HOME/.config/idlisseus" ]; then
    docker exec --user root "$NAME" sh -c 'mkdir -p /opt/data/.config/idlisseus' 2>/dev/null || true
    for f in ebird dryad skyfi; do
      [ -f "$HOME/.config/idlisseus/$f.json" ] && docker cp "$HOME/.config/idlisseus/$f.json" "$NAME":/opt/data/.config/idlisseus/"$f".json 2>/dev/null || true
    done
    docker exec --user root "$NAME" sh -c 'chown -R 10000:10000 /opt/data/.config/idlisseus' 2>/dev/null || true
  fi
}

# --restart: recreate and exit
if [ "${1:-}" = "--restart" ]; then start_container; echo "[chat] $NAME recreated"; exit 0; fi

# ensure the persistent container is up
docker ps --filter "name=^${NAME}$" --filter status=running -q | grep -q . || start_container

# ── assembled "smart bookends, cheap middle" mode ──────────────────────────────────────────────
# --smart-model / --cheap-model enable the 3-stage loop (clarify-gate → cheap runner → synthesizer).
# Both default to qwen122b if unset. Absent both flags, chat.sh runs the normal single-model path.
SMART_MODEL=""; CHEAP_MODEL=""
while true; do
  case "${1:-}" in
    --smart-model) SMART_MODEL="${2:-}"; shift 2 ;;
    --cheap-model) CHEAP_MODEL="${2:-}"; shift 2 ;;
    *) break ;;
  esac
done
if [ -n "$SMART_MODEL" ] || [ -n "$CHEAP_MODEL" ]; then
  SMART_MODEL="${SMART_MODEL:-qwen122b}"; CHEAP_MODEL="${CHEAP_MODEL:-qwen122b}"
  ASM="$(cd "$HERE/../../benchmarks/eastern_ghats_run" && pwd)/assembled.py"
  echo "[chat] assembled mode — smart=$SMART_MODEL · cheap=$CHEAP_MODEL (container $NAME)" >&2
  if [ "$#" -gt 0 ]; then exec python3 "$ASM" -q "$*" --smart "$SMART_MODEL" --cheap "$CHEAP_MODEL"
  else exec python3 "$ASM" repl --smart "$SMART_MODEL" --cheap "$CHEAP_MODEL"; fi
fi

# model selection — the model is set EXPLICITLY on every call (deterministic), never inherited from
# config default or a prior /model switch. Each invocation is a FRESH session unless CONTINUE=1.
MODEL="${MODEL:-}"
if [ "${1:-}" = "--model" ] || [ "${1:-}" = "-m" ]; then MODEL="${2:-}"; shift 2; fi
# guard: any other leading flag (e.g. --agent) is a mistake — don't silently send it as the query
if [ -n "${1:-}" ] && [ "${1}" != "${1#-}" ]; then
  echo "chat.sh: unknown option '${1}' — did you mean --model? (see --help)" >&2; exit 2
fi
MFLAGS=(); LABEL=""
case "$MODEL" in
  ""|qwen|qwen122b|122b|local)          MFLAGS=(-m qwen --provider custom);             LABEL="qwen-122b-local" ;;
  glm5.2|glm-5.2|glm)                    MFLAGS=(-m z-ai/glm-5.2 --provider openrouter); LABEL="glm-5.2 (openrouter)" ;;
  deepseekv4|deepseek-v4|deepseek|dsv4)  MFLAGS=(-m deepseek/deepseek-v4-flash --provider openrouter); LABEL="deepseek-v4-flash (openrouter)" ;;
  */*)                                   MFLAGS=(-m "$MODEL" --provider openrouter);     LABEL="$MODEL (openrouter)" ;;
  *)  echo "chat.sh: unknown --model '$MODEL' (use qwen122b | deepseekv4 | glm5.2 | <provider/slug>)" >&2; exit 2 ;;
esac
[ "${AUTO_APPROVE:-0}" = "1" ] && MFLAGS+=(--yolo)
[ "${CONTINUE:-0}" = "1" ] && MFLAGS+=(-c)
[ -n "${HERMES_SOURCE:-}" ] && MFLAGS+=(--source "$HERMES_SOURCE")   # bench: unique per-run session tag
[ -n "${HERMES_RESUME:-}" ] && MFLAGS+=(--resume "$HERMES_RESUME")   # multi-turn: continue a specific session
[ -n "${HERMES_MAXTURNS:-}" ] && MFLAGS+=(--max-turns "$HERMES_MAXTURNS")  # cap tool-loop iterations (discipline mechanism)
echo "[chat] backend=$LABEL (container $NAME)  ·  flags: ${MFLAGS[*]}" >&2

if [ "$#" -gt 0 ]; then
  docker exec "$NAME" hermes chat "${MFLAGS[@]}" -q "$*"
else
  docker exec -it "$NAME" hermes chat "${MFLAGS[@]}"
fi
