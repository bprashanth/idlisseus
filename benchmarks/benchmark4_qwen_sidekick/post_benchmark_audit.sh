#!/bin/bash
# Post-benchmark security audit: diff system state before vs after a Hermes session.
# Reports new packages, new hermes files, new pip packages, and new cron/hook entries.
#
# Usage:
#   post_benchmark_audit.sh <pre_dpkg_file> <pre_hermes_files> <pre_marker> <output_file>
#
# Arguments:
#   pre_dpkg_file      — dpkg --get-selections output from before the run
#   pre_hermes_files   — find ~/.hermes/skills ~/.hermes/hooks output from before
#   pre_marker         — a file whose mtime marks the start of the benchmark
#   output_file        — where to write the audit report

set -uo pipefail

PRE_DPKG="${1:-}"
PRE_HERMES="${2:-}"
PRE_MARKER="${3:-}"
OUTPUT="${4:-/tmp/hermes_audit.txt}"

log() { echo "[audit] $*"; }

{
echo "=== Hermes Post-Benchmark Security Audit ==="
echo "Generated: $(date)"
echo ""

# ── 1. New system packages ──────────────────────────────────────────────────
echo "## 1. New system packages (apt/dpkg)"
if [ -f "$PRE_DPKG" ]; then
  dpkg --get-selections | sort > /tmp/post_dpkg.txt
  NEW_PKG=$(diff "$PRE_DPKG" /tmp/post_dpkg.txt | grep '^>' | sed 's/^> /  /' || true)
  if [ -n "$NEW_PKG" ]; then
    echo "WARNING: new packages installed during benchmark:"
    echo "$NEW_PKG"
  else
    echo "CLEAN: no new system packages."
  fi
else
  echo "SKIP: no pre-benchmark dpkg snapshot found."
fi
echo ""

# ── 2. New Hermes skills and hooks ─────────────────────────────────────────
echo "## 2. New files in ~/.hermes/skills and ~/.hermes/hooks"
if [ -f "$PRE_HERMES" ]; then
  sudo find /home/beeps/.hermes/skills /home/beeps/.hermes/hooks 2>/dev/null | sort \
    > /tmp/post_hermes_files.txt
  NEW_FILES=$(diff "$PRE_HERMES" /tmp/post_hermes_files.txt | grep '^>' | sed 's/^> /  /' || true)
  if [ -n "$NEW_FILES" ]; then
    echo "WARNING: new skills/hooks created during benchmark:"
    echo "$NEW_FILES"
    echo ""
    echo "Contents of new files:"
    while IFS= read -r line; do
      file=$(echo "$line" | sed 's/^  //')
      if sudo test -f "$file"; then
        echo "--- $file ---"
        sudo head -30 "$file"
        echo ""
      fi
    done <<< "$NEW_FILES"
  else
    echo "CLEAN: no new skills or hooks."
  fi
else
  echo "SKIP: no pre-benchmark hermes files snapshot found."
fi
echo ""

# ── 3. New cron entries ─────────────────────────────────────────────────────
echo "## 3. Cron entries"
sudo ls /home/beeps/.hermes/cron/ 2>/dev/null | head -20 || true
CRON_COUNT=$(sudo ls /home/beeps/.hermes/cron/ 2>/dev/null | wc -l || echo 0)
if [ "$CRON_COUNT" -gt 0 ]; then
  echo "WARNING: $CRON_COUNT cron entries found in ~/.hermes/cron/"
  sudo ls -la /home/beeps/.hermes/cron/ 2>/dev/null || true
else
  echo "CLEAN: no cron entries."
fi
echo ""

# ── 4. New pip packages (inside the hermes container baseline image) ────────
echo "## 4. Pip packages installed inside Hermes's venv"
# Hermes uses its own venv inside /opt/hermes — we can snapshot via docker
HERMES_PIP=$(docker run --rm -v /home/beeps/.hermes:/opt/data \
  nousresearch/hermes-agent bash -c "pip list 2>/dev/null || true" 2>/dev/null || echo "could not run pip list")
echo "$HERMES_PIP" | head -100
echo ""

# ── 5. Files written by model to ~/.hermes/ after the benchmark marker ──────
echo "## 5. Files written to ~/.hermes/ after benchmark start"
if [ -f "$PRE_MARKER" ]; then
  echo "(files newer than $PRE_MARKER — excludes wildfire_research, sessions, logs)"
  sudo find /home/beeps/.hermes/ -newer "$PRE_MARKER" \
    -not -path '*/wildfire_research*' \
    -not -path '*/sessions*' \
    -not -path '*/logs*' \
    -not -path '*/cache*' \
    -not -path '*/state.db*' \
    -not -path '*/archived_*' \
    -not -path '*/h2h_*' \
    2>/dev/null | head -50 || true
else
  echo "SKIP: no pre-benchmark marker found."
fi
echo ""

# ── 6. Lingering processes ──────────────────────────────────────────────────
echo "## 6. Lingering Hermes or model processes"
PROCS=$(pgrep -af "hermes|vllm|qwen" 2>/dev/null || true)
if [ -n "$PROCS" ]; then
  echo "WARNING: lingering processes:"
  echo "$PROCS"
else
  echo "CLEAN: no hermes/vllm/qwen processes running."
fi
echo ""

# ── 7. Docker containers ────────────────────────────────────────────────────
echo "## 7. Running Docker containers"
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null || true
echo ""

echo "=== Audit complete ==="

} | tee "$OUTPUT"

echo ""
log "Audit written to $OUTPUT"
