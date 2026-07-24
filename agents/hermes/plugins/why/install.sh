#!/usr/bin/env bash
# Install the `why` plugin into the running Hermes home and enable it.
# Source of truth is this dir; Hermes loads user plugins from ~/.hermes/plugins/.
# ~/.hermes is owned by the sandbox user (uid 10000), so we sudo the copy + chown.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.hermes/plugins/why"

sudo mkdir -p "$HOME/.hermes/plugins"
sudo cp "$HERE"/plugin.yaml "$HERE"/__init__.py "$HERE"/ledger.py "$DEST"/ 2>/dev/null || {
  sudo mkdir -p "$DEST"; sudo cp "$HERE"/plugin.yaml "$HERE"/__init__.py "$HERE"/ledger.py "$DEST"/; }
sudo rm -rf "$DEST/__pycache__"
sudo chown -R 10000:10000 "$HOME/.hermes/plugins"
echo "installed -> $DEST"

# enable it (writes to ~/.hermes/config.yaml plugins.enabled). Runs Hermes once, headless.
docker run --rm -v "$HOME/.hermes:/opt/data" -e HOME=/opt/data \
  --entrypoint bash "${HERMES_IMAGE:-hermes-agent-local}" -c "hermes plugins enable why" \
  2>/dev/null | tail -1 || echo "(enable step: run 'hermes plugins enable why' if needed)"
echo "done — /why takes effect on the next chat session."
