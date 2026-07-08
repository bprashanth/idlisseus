#!/usr/bin/env bash
# Print the /why for the last answer (same output as the /why command) — for quick testing.
LED="$HOME/.hermes/work/.why_ledger.json"
TMP="$(mktemp)"; sudo cat "$LED" > "$TMP" 2>/dev/null
python3 "$(dirname "$0")/ledger.py" "$TMP"; rm -f "$TMP"
