#!/usr/bin/env bash
# Struggle detector (NOTES.md §5), factored out so it can be re-scored over saved
# logs. Prints "STRUGGLED=yes|no  reason=..." to stdout.
#
# Usage: detect_struggle.sh <log> <rc> <dur_s> [T_struggle=480]
#
# Scans only the AGENT output: container plumbing (s6 init/teardown) is stripped
# first, because those lines contain words like "unable to"/"fatal" that are NOT
# the agent giving up — matching them was a false positive on a correct run.
set -uo pipefail
LOG="${1:?log}"; RC="${2:?rc}"; DUR="${3:?dur}"; T="${4:-480}"

CLEAN="$(grep -avE 's6-rc|s6-applyuidgid|legacy-services|legacy-cont-init|cont-init|fix-attrs|oneshot-runner|preparing terminal' "$LOG" 2>/dev/null || true)"

struggled="no"; reason=""
add(){ struggled="yes"; reason="${reason:+$reason,}$1"; }

[ "$RC" = "124" ] && add "timeout"
[ "$DUR" -gt "$T" ] && add "slow(${DUR}s>${T}s)"
grep -qiE 'could not|unable to|incomplete|as a proxy|gave up|fell back|fall back|was unable|did not complete|no numeric|couldn'\''t (compute|complete|finish|get)' <<<"$CLEAN" && add "failure_phrase"
grep -qE '[0-9]' <<<"$CLEAN" || add "no_numeric_answer"

echo "STRUGGLED=$struggled  reason=${reason:-none}"
