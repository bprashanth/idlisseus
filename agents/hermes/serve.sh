#!/usr/bin/env bash
# serve.sh — ensure the always-on map server is running (tmux session on 127.0.0.1:8000, serving the dir
# where the agent writes lens maps: agents/hermes/gt). Idempotent: run it any time.
#
#   agents/hermes/serve.sh            # start (or confirm) the server
#   agents/hermes/serve.sh restart    # restart it (rarely needed — new maps appear automatically)
#   agents/hermes/serve.sh stop
#
# View from your laptop:  ssh -L 8000:localhost:8000 <user>@<box>  →  http://localhost:8000/
# Binds to 127.0.0.1 only (through the SSH tunnel; never public).
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DIR="$HERE/gt"; PORT=8000; SESS=mapserver
mkdir -p "$DIR"

case "${1:-start}" in
  stop)    tmux kill-session -t "$SESS" 2>/dev/null && echo "stopped"; exit 0 ;;
  restart) tmux kill-session -t "$SESS" 2>/dev/null ;;
esac

if tmux has-session -t "$SESS" 2>/dev/null; then
  echo "already running (tmux: $SESS)"
else
  tmux new-session -d -s "$SESS" "cd '$DIR' && python3 -m http.server $PORT --bind 127.0.0.1"
  sleep 1; echo "started (tmux: $SESS)"
fi
echo "serving $DIR on http://127.0.0.1:$PORT"
echo "maps: $(ls -1 "$DIR"/*.html 2>/dev/null | sed 's#.*/##' | tr '\n' ' ' || echo none)"
echo "laptop:  ssh -L $PORT:localhost:$PORT $USER@<box>  then open http://localhost:$PORT/"
