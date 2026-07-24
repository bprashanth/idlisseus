#!/usr/bin/env bash
# Moved: the canonical runner is agents/hermes/chat.sh (persistent container, --model aware, /model
# switching, live-mounted connectors). This forwards there so old paths/muscle-memory keep working.
#   chat.sh --model deepseekv4 "…"   ·   chat.sh --help
HERE="$(cd "$(dirname "$0")" && pwd)"
exec "$HERE/../../agents/hermes/chat.sh" "$@"
