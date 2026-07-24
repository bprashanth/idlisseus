#!/usr/bin/env bash
# Install the `discipline` plugin into the running Hermes home and enable it.
# Source of truth is this dir; Hermes loads user plugins from ~/.hermes/plugins/ (container /opt/data/plugins).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
NAME="${HERMES_CONTAINER:-hermes-live}"
sudo docker exec "$NAME" sh -c 'mkdir -p /opt/data/plugins/discipline'
sudo docker cp "$HERE/plugin.yaml"  "$NAME":/opt/data/plugins/discipline/plugin.yaml
sudo docker cp "$HERE/__init__.py"  "$NAME":/opt/data/plugins/discipline/__init__.py
sudo docker exec --user root "$NAME" sh -c 'chown -R 10000:10000 /opt/data/plugins/discipline; rm -rf /opt/data/plugins/discipline/__pycache__'
sudo docker exec "$NAME" sh -c 'hermes plugins enable discipline' 2>&1 | tail -1
echo "installed + enabled -> takes effect on the next chat session (edit __init__.py + re-run to update)."
