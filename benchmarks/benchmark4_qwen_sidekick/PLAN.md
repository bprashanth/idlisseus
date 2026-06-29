# Benchmark 4: Qwen ds4-replacement + sidekick, ds4 SSD streaming, Nemotron retry

User is offline ~2-3h. Work through stages in order, checkpoint after every step (not just
phase boundaries) into `CHECKPOINT.md` in this directory. If interrupted/context-compacted,
read `CHECKPOINT.md` first before doing anything else.

**Net result constraint: install exactly 2 new models** — Qwen3-Next-80B-A3B-Instruct-FP8 (ds4
replacement) and Qwen3.5-2B (sidekick). Nemotron-3 is already installed/cached from Benchmark 2
(retry, not a new install).

## Stage 1: Big Qwen (ds4 replacement) — install, smoke test, agentic benchmark

1. Stop ds4 (`sudo systemctl stop ds4`).
2. Pull/run `TheClusterDev/Qwen3-Next-80B-A3B-Instruct-FP8` (80.5GB) via vLLM, single GPU,
   bound to `172.17.0.1:8000` (same pattern as Nemotron/Seed-OSS). Check for an official
   Qwen3-Next vLLM serving guide first (architecture is newer/hybrid — may need specific flags
   e.g. for the linear-attention layers); adapt rather than guessing blind.
3. Watch for the known download-stall pattern (cache-dir size flat >10min while container
   "Up" — checked via `.incomplete` blob mtimes) — restart container to resume if it happens.
4. Smoke test: `/v1/models` (context_length), non-streaming + streaming `/v1/chat/completions`.
5. **Check `free -h` for actual leftover RAM with Qwen loaded.** As a diagnostic (not a
   permanent config): try also starting `ds4-server` with `--ssd-streaming
   --ssd-streaming-cache-experts <N>GB` sized to fit in whatever headroom remains, see if it
   actually loads successfully alongside big-Qwen. Record the result (works / doesn't fit /
   how much cache it would need) then stop that diagnostic ds4 instance — this is exploratory,
   not the final config; don't run it concurrently through the actual benchmark.
6. Point Hermes at `qwen3-next-80b` (`sudo python3 deploy/hermes/point_at_model.py
   qwen3-next-80b http://172.17.0.1:8000/v1`), run the two-step Hermes smoke test (trivial
   prompt, then tool-calling test) — GO/NO-GO gate, stop and report on a real failure.
7. Run the full wildfire-research agentic task via Hermes+Qwen (identical prompt to
   Benchmark 2 Phase 3/10 — see `benchmark2_hermes/CHECKPOINT.md` for exact wording). **Do not
   re-run raw ds4 or Hermes+ds4 — that data already exists.** Qwen has no native agent CLI of
   its own (same situation as Nemotron), so only the Hermes-wrapped condition applies here.
8. Save outputs to `benchmark4_qwen_sidekick/qwen_big_results/`, checkpoint elapsed time, tool
   call count, citation accuracy, dashboard quality — same audit rigor as prior rounds.
9. Stop the Qwen container, free memory, before moving to Stage 2.

## Stage 2: Normal ds4 + sidekick (Qwen3.5-2B) — install, smoke test, light benchmark

1. Start ds4 normally (no streaming). Confirm `free -h` shows ~13GB available (the established
   baseline).
2. Pull/run `Qwen/Qwen3.5-2B` (4.57GB BF16, full precision) via vLLM, single GPU, bound to
   `172.17.0.1:8001` (**different port** — ds4 already owns 8000).
3. Smoke test on port 8001.
4. Run a **light** task battery — short queries, wordsmithing, one-paragraph summaries, simple
   data/arithmetic, a mock API-call-style structured-output prompt. Explicitly do NOT give it
   large documents or multi-thousand-token synthesis tasks — that's not its role and the user
   asked not to over-task it. ~5-6 short prompts is plenty; save prompt+response pairs to
   `benchmark4_qwen_sidekick/sidekick_results/`.
5. Checkpoint: does it actually coexist with ds4 without OOM, what's the real combined memory
   use, response latency for each prompt.

## Stage 3: ds4 + `--ssd-streaming` — does it actually free enough RAM to matter?

1. Stop normal ds4. Start it with `--ssd-streaming --ssd-streaming-cache-experts <N>GB` (start
   with something like 20-30GB given this box has far more headroom than the MacBook examples
   in ds4's own docs — check the startup log's cache report, ds4 may auto-adjust).
2. Measure: actual `free -h` RAM used vs. normal ds4's ~108GB baseline (how much did streaming
   actually save?), and decode speed — repeat the same short-prompt latency test used in
   Benchmark 3 (`"What is 2+2?"` etc.) plus a single-stream throughput check, compare directly
   against ds4's established ~15 tok/s non-streaming baseline.
3. **Decision point:** if the RAM saved is large and the speed penalty is small, consider
   whether a *bigger* sidekick (4B/9B) now fits in the larger freed headroom, and note it as a
   possible upgrade — but do not feel obligated to actually swap the sidekick model out just to
   prove the point. If the speed penalty is severe relative to the RAM gained, or the freed
   headroom doesn't meaningfully change what sidekick fits, **say so plainly and stop here** —
   per the user's explicit instruction, don't force a streaming-based final config if it isn't
   worth it. Either way this is a measurement-and-judgment step, not an obligation to adopt
   streaming permanently.
4. Checkpoint the actual numbers either way — this is useful data regardless of the verdict.
5. Restore ds4 to normal (non-streaming) mode when done, since that's the safer default unless
   Stage 3 clearly justifies switching.

## Stage 4: Nemotron-3 retry without speculative decoding — time-boxed

Already-cached model/image from Benchmark 2 — no new install.

1. Stop whatever's running. Start Nemotron-3 via vLLM with the **same config as
   `deploy/nemotron-3-super/run.sh` but WITHOUT `--speculative_config`** (this was the
   suspected root cause of Benchmark 2's throughput collapse under long context).
2. Smoke test (same two-step direct API check).
3. Point Hermes at it, run the two-step Hermes smoke-test gate.
4. Run the wildfire research task, but **time-box it explicitly**: if by ~40-45 minutes elapsed
   it's clearly tracking far worse than ds4's 25min/Hermes+ds4's 79min pace (e.g. <25% as much
   progress by tool-call count / files downloaded as Hermes+ds4 had at the equivalent elapsed
   time), stop it and document "still not competitive even without speculative decoding" rather
   than letting it run for hours. We already have two working big-model candidates (ds4,
   Qwen-big) — this is a confirmatory check, not a must-finish experiment.
5. Checkpoint the outcome either way (worked / still too slow / how it compared at the cutoff).
6. Restore ds4 as the final running state when this stage concludes (see "Final state" below).

## Final state when all stages are done (or time runs out)

Restore **ds4 running normally (no streaming)**, pointed-at by Hermes and Odysseus, matching
the established checkpoint convention from prior rounds — unless Stage 2/3 produced a clearly
better permanent sidekick configuration the user would want left running for them to see; if so,
leave that running too instead and say so prominently in the final checkpoint entry.

## Reporting

Write `benchmark4_qwen_sidekick/REPORT.md` only once all stages (or their time-boxed cutoffs)
are done — summarizing, for each stage, what was measured, real numbers, and a direct verdict
on whether each piece (big-Qwen replacement, sidekick, SSD streaming, Nemotron-retry) is worth
adopting. Keep `CHECKPOINT.md` updated continuously throughout — it is the source of truth if
this work is interrupted before the report is written.
