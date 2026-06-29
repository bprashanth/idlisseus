# Checkpoint log — Benchmark 4 (Qwen replacement + sidekick, SSD streaming, Nemotron retry)

Read this first if context has been compacted. User is offline ~2-3h as of start — work through
`PLAN.md`'s stages in order async, checkpoint continuously. Append-only, don't rewrite history.

## 2026-06-25 12:15 — Started, Stage 1 in progress

- Disk: 559GB free at start (plenty for 2 new ~80GB-class downloads). ds4 stopped, 117GB free.
- **Real bug found and fixed:** `Qwen/Qwen3-Next-80B-A3B-Instruct-FP8` crashes immediately on
  load with vLLM's recipe-page-recommended env vars (`VLLM_USE_FLASHINFER_MOE_FP8=1` etc.) —
  `ValueError: FP8 MoE backend FLASHINFER_CUTLASS does not support the deployment configuration`
  (this GPU falls back from FLASHINFER_TRTLLM to CUTLASS for MoE, and CUTLASS doesn't support
  this checkpoint's specific FP8 block-quant scheme). **Fix: `--moe-backend marlin` explicit
  flag** (same backend that worked for Nemotron-3's MoE in Benchmark 2) instead of the env-var
  approach — confirmed past the crash point, now downloading. `deploy/qwen3-next-80b/run.sh`
  updated with this fix and a comment explaining why.
- Container `qwen-big-vllm` now downloading ~80.5GB to `~/.cache/huggingface`. Bound to
  `172.17.0.1:8000`. No `--speculative-config`/MTP (deliberately avoided per Nemotron's
  Benchmark 2 failure mode).
- **Next:** wait for download, smoke test (`/v1/models`, non-streaming + streaming chat), check
  `free -h` for leftover headroom, diagnostic-test whether `ds4 --ssd-streaming` could also fit
  in that headroom (Stage 1 step 5 in PLAN.md), point Hermes at it
  (`sudo python3 deploy/hermes/point_at_model.py qwen3-next-80b http://172.17.0.1:8000/v1`),
  two-step Hermes smoke test, then the full wildfire-research agentic task (identical prompt to
  Benchmark 2 — see `benchmark2_hermes/CHECKPOINT.md` for exact wording), saved to
  `qwen_big_results/`.
- ds4-server currently DOWN (deliberately). Odysseus/Hermes still configured pointing at
  `deepseek-v4-flash` from before this session started — will need re-pointing once Stage 1's
  Hermes testing begins (point_at_model.py to qwen3-next-80b, then back to deepseek-v4-flash
  for Stage 2, etc. — track carefully which model Hermes/Odysseus actually point at each stage).
- **Remaining stages not yet started:** Stage 2 (normal ds4 + Qwen3.5-2B sidekick on port 8001),
  Stage 3 (ds4 `--ssd-streaming` RAM/speed measurement, decide if worth it), Stage 4 (Nemotron-3
  retry without speculative decoding, time-boxed ~40-45min cutoff if clearly underperforming).
- Final state target: ds4 running normally, Hermes/Odysseus pointed at it — unless an earlier
  stage clearly produces a better permanent config worth leaving running instead (say so loudly
  in the final entry if so).

## 2026-06-25 12:48 — Download progressing normally

- 17GB of 80.5GB after 28min, no errors, container alive. Continuing to wait.

## 2026-06-25 13:14 — Still downloading, ~88min remaining at current pace

- 31GB of 80.5GB after 53min (~0.56GB/min steady). No errors, container alive. ETA ~88 more
  minutes for download alone, then engine warmup. Continuing to wait.

## 2026-06-25 13:55 — Download stall #2, recovered via container restart

- Same pattern as Nemotron's Benchmark 2 stall: 8 large blobs all stuck at byte-identical sizes
  across two checks 90s apart (confirmed via exact `du -sb` byte counts, not just human-rounded
  `du -sh`). Stalled at 37.6GB of 80.5GB after ~1h20m.
- Fix applied: `docker stop qwen-big-vllm` (--rm, auto-removed) then re-ran
  `deploy/qwen3-next-80b/run.sh` (already has the moe-backend marlin fix baked in). New
  container id 0cd705a8c0ad.
- Waiting to confirm download actually resumes growing post-restart (background watcher
  bs1u1mqw5). This vLLM-nightly + HF-downloader + this-network combination has now stalled on
  2 of 2 large downloads attempted (Nemotron in Benchmark 2, now Qwen here) - worth treating
  this as an expected, recurring characteristic of large downloads on this box, not a fluke -
  always budget time for at least one stall-and-restart cycle on any ~70GB+ download here.

## 2026-06-25 14:01 — Restart did NOT resume from 37.6GB — reset to ~5.8GB

- Correction to the assumption from Benchmark 2 (where restarting resumed cleanly): this time
  the restart reset ALL the previously-stuck blobs back to 0 rather than resuming via range
  request - now at 5.8GB after 21min on the new container, having lost the prior ~37.6GB of
  progress. huggingface_hub's resume behavior on this download appears inconsistent (sometimes
  resumes cleanly, sometimes restarts stuck blobs from scratch) - don't assume a restart is free,
  budget for a possible full-or-partial re-download when one happens.
- Confirmed no longer flat (was 37.6GB stalled, now 5.8GB and presumably growing) - checking
  growth rate next. Continuing to wait for completion.

## 2026-06-25 20:06 — Stall #2 confirmed, trying a different fix this time

- 7 of 8 blobs flat since ~19:26-19:34 (30+ min ago), 1 blob continued alone until ~20:05 then
  also appears stopped. ~5.9GB total, essentially unchanged since the post-reset restart 48min
  ago. This is now 2 stalls + 1 costly full reset on this single download - disproportionate
  time spent vs the 2-3h total budget for this whole 4-stage round.
- **Trying a different fix instead of repeating the same restart**: adding
  `-e HF_HUB_ENABLE_HF_TRANSFER=0` to disable the accelerated parallel multi-connection
  downloader, falling back to huggingface_hub's standard single-connection-per-file resumable
  downloader. Hypothesis: the multi-stream accelerated client is the actual source of these
  stalls on this network (consistent with multiple blobs dying around the same time each
  occurrence), and a slower-but-more-robust path may net out faster than repeated resets.
- **Adaptive plan if this also stalls quickly**: deprioritize Stage 1's big-Qwen agentic
  benchmark (leave the download running in the background at whatever pace it manages) and pivot
  to Stages 2-4 (sidekick, SSD streaming, Nemotron retry) which don't depend on this download,
  to make better use of the remaining time. Return to Stage 1 afterward if time permits.

## 2026-06-25 20:19 — hf_transfer fix didn't help either; deprioritizing Stage 1, pivoting to Stage 2

- After disabling HF_HUB_ENABLE_HF_TRANSFER, size actually DROPPED further (6.28GB -> 4.5GB over
  10min) rather than growing - the standard downloader fallback appears to have discarded/
  reinterpreted some of the hf_transfer-written partial blobs as invalid rather than resuming
  them. This fix did not help; if anything made things worse.
- **Decision per the adaptive plan: stop babysitting this download.** Leaving container
  `qwen-big-vllm` running untouched in the background at whatever pace it manages — no more
  restarts for now, since each restart attempt so far has cost progress rather than helping.
  Will check back on it later; if it eventually completes on its own, great, otherwise Stage 1's
  agentic benchmark may end up skipped/deferred for this round given the time already spent.
- **Real lesson for docs/models.md / PLAN_MODEL.md**: this network's download stalls are not
  reliably fixed by simple container restarts, and disabling hf_transfer is not a clean fix
  either — both can cause partial resets rather than clean resumes. Treat any ~70GB+ download
  on this box as having a real chance of taking 2-3x its naive ETA once stall/restart overhead
  is included, and don't assume any specific remediation is safe/lossless.
- **Pivoting to Stage 2 now**: ds4 has been stopped this whole time (needed for the Qwen-replacement
  work) — starting it normally, then bringing up Qwen3.5-2B sidekick on port 8001 alongside it.

## 2026-06-25 16:28 — Stage 2 started (context resumed from compacted session)

- On context resume: confirmed ds4 is `active` and responsive (`/v1/models` returns both model
  IDs). Memory: 107Gi used, 13Gi free — matches expected ds4 baseline exactly.
- No qwen-big-vllm container running (it had already been stopped/removed before the session
  ended). The ~4.6GB of partial Qwen3-Next-80B cache remains in ~/.cache/huggingface — leaving
  it; not re-starting Stage 1 download for now, too many stall/reset cycles already.
- Port 8001 free. Launched `qwen-sidekick-vllm` container via new
  `deploy/qwen3.5-2b/run.sh`: Qwen/Qwen3.5-2B (4.57GB BF16) on 172.17.0.1:8001.
  Critical memory flags: `--gpu-memory-utilization 0.09` (caps vLLM's KV cache budget to ~9%
  of 121GB unified pool = ~10.9GB total, so model weights + KV cache ≈ 11GB, within 13GB gap)
  and `--max-model-len 8192` (short prompts only, no need for large context).
- Light battery script written: `benchmark4_qwen_sidekick/run_sidekick_battery.py` — 6 short
  tasks: short_query, wordsmithing, short_summary, arithmetic, structured_output,
  translation_short. No large documents embedded.
- Waiting for download (~4.6GB) + vLLM startup to complete. Monitoring container logs for
  "Application startup complete" or OOM/crash signals.

## 2026-06-25 22:44 — CRITICAL LESSON: HF download stall root cause identified and fixed

**Root cause of all prior download stalls (Qwen3-Next-80B, Qwen3.5-2B attempts):**
The `hf_transfer` Rust parallel downloader opens multiple TCP connections to HuggingFace's
CDN and buffers all data in Python process memory BEFORE writing to the .incomplete file.
When connections stall (CDN session expiry / rate limiting), the entire download hangs with
large memory footprint but 0 bytes on disk. Restarting the container discards all buffered
data and only the small on-disk portion is retained. HuggingFace's CDN appears to throttle
or drop parallel connections from this network (DGX Spark), causing systematic stalls.

**The `hf` CLI tool (v1.21.0, replacing `huggingface-cli`) has the SAME problem:** despite
`HF_HUB_ENABLE_HF_TRANSFER=0`, the new `hf` CLI also opens 28+ parallel connections and
buffers data in memory. The env var no longer controls this behavior in v1.21.0.

**The fix that works: `wget -c` directly on the raw file URL.**
wget opens a SINGLE TCP connection, streams bytes directly to disk, and supports clean
byte-range resume with `-c` (sends `Range: bytes=N-` where N is current file size). No
memory buffering, no stalls from parallel connection management. Reliable on this network.

**Download procedure (do this instead of any hf_transfer / hf CLI approach):**
1. Stop ds4 first (`sudo systemctl stop ds4`) — frees 93GB, download has no memory pressure
2. Fix HF cache permissions if needed: `sudo chown -R beeps:beeps ~/.cache/huggingface/`
3. Run the wget script: `bash deploy/qwen3.5-2b/wget_download.sh` (small model) or
   `bash deploy/qwen3-next-80b/wget_download.sh` (big model, 8 shards × ~10.7GB)
4. Run `HF_HUB_ENABLE_HF_TRANSFER=0 hf download <model>` ONCE after wget to create
   the snapshot/ symlinks (it skips the already-downloaded blobs, just creates symlinks)
5. Start ds4 back (`sudo systemctl start ds4`), then start vLLM pointing at cached model

**Models and their blob hashes (from HF API /tree endpoint):**
- Qwen/Qwen3.5-2B: single shard `model.safetensors-00001-of-00001.safetensors`
  → blob `aa33250c4fc64891ddfaba3a314fd9542ea371843c387178b425fbcc5ed680b1` (4.57GB)
- Qwen/Qwen3-Next-80B-A3B-Instruct-FP8: 8 shards, see `deploy/qwen3-next-80b/wget_download.sh`

**DO NOT use:**
- `hf download` / `huggingface-cli download` for large model files — both buffer to memory
- `docker run vllm/... --model <X>` for first-time downloads — hf_transfer always used
- Container restart as a fix for stalled downloads — discards buffered progress

**Status (as of 23:09):** Qwen3.5-2B download COMPLETE — 4,548,221,488 bytes on disk.
The earlier estimate of 4.57GB was wrong; actual size is 4.23GB (CDN returned 416 when resumed
at 4.55GB because that IS the file size — download was done). HF snapshot symlinks created via
`HF_HUB_ENABLE_HF_TRANSFER=0 hf download Qwen/Qwen3.5-2B`.

**Throttle reset behavior discovered (critical):**
HF CDN throttle resets after ~40-45 minutes of inactivity. After a throttle (speed drops to
~70-80 KB/s), killing wget and restarting immediately still gets throttled (IP-based, not
connection-based). But waiting ~40 minutes and restarting wget gets a fresh burst (~8 MB/s).
The burst allowance appears to be ~1.7-2GB per period. ModelScope has the SAME throttle
behavior (~70-80 KB/s sustained, no burst allowance). Conclusion: for large model downloads on
this network, use wget -c and plan for one stall + 45-min wait if the file is over ~2GB. Do NOT
restart immediately after throttle — wait 40-45 min for the reset.

## 2026-06-25 23:15 — Stage 2 (sidekick battery + concurrent test) COMPLETE

**Setup:** ds4 running normally on port 8000 (108GB), Qwen3.5-2B vLLM sidekick on port 8001.
- Sidekick container: `vllm/vllm-openai:cu130-nightly`, `--gpu-memory-utilization 0.08` (critical:
  0.09 fails with "Free memory 10.58/121.63 GiB < desired 10.95 GiB" — use 0.08 for headroom)
- Startup took ~99 seconds (model load 20s + torch.compile 20s + profiling/warmup 34s + graphs 1s)
- KV cache at 0.08 utilization: 67,456 tokens, 26x max concurrency for 8192-token requests
- Combined memory: 118GB used, 3.3GB available — tight but stable, no OOM

**Battery test results (sequential, port 8001 only):**
| Task | Elapsed | Tokens | Speed | Quality |
|------|---------|--------|-------|---------|
| short_query | 2.1s | 96 | 44.7 tok/s | POOR (hallucinations: "borignè", "mothwood") |
| wordsmithing | 0.5s | 22 | 41.6 tok/s | GOOD |
| short_summary | 1.3s | 43 | 32.8 tok/s | EXCELLENT |
| arithmetic | 9.4s | 429 | 45.8 tok/s | GOOD (verbose step-by-step, correct) |
| structured_output | 2.0s | 90 | 44.7 tok/s | EXCELLENT (clean JSON) |
| translation_short | 3.5s | 158 | 45.2 tok/s | POOR (garbled Hindi, mixed scripts) |

**Concurrent test (ds4 + sidekick simultaneously):**
- Wall time: 18.1s for both requests
- ds4: 119 tokens in 18.1s = **6.6 tok/s** (down from 15 tok/s alone, -56%)
- sidekick: 374 tokens in 18.0s = **20.8 tok/s** (down from 44.7 tok/s alone, -53%)
- Both degraded ~50% due to memory bandwidth contention on GB10's unified pool
- No OOM, no crash, no errors — proved concurrent operation is feasible

**Verdict for Stage 2:**
- The sidekick fits (barely — 3.3GB margin) and works without OOM.
- Sidekick is fast for short tasks (33-46 tok/s sequential) but slows significantly under concurrency.
- Quality appropriate for wordsmithing and structured extraction; too small for factual queries or
  non-English translation. 2B is right for low-stakes formatting tasks, wrong for knowledge tasks.
- Concurrency causes ~50% mutual slowdown — users sending queries to both endpoints simultaneously
  will get notably degraded experience. Sequential routing (one endpoint at a time) avoids this.
- Results saved to `benchmark4_qwen_sidekick/sidekick_results/`

## 2026-06-25 23:00 — Stage 3 (SSD streaming) results

**SSD streaming tested with 20GB and 60GB expert caches. Summary:**

| Metric | Normal mode | SSD streaming 20GB cache | SSD streaming 60GB cache |
|--------|-------------|--------------------------|--------------------------|
| RAM at startup | 108GB | 13GB | 13GB |
| RAM after warmup (2-3 prompts) | 108GB | 81GB | 83GB |
| Startup time | ~2 min (mmap full model) | < 1 sec | < 1 sec |
| tok/s (1st prompt) | ~15 | 3.1-3.4 | 3.1 |
| tok/s (2nd prompt, warmed) | ~15 | 8.5 | ~8-9 |
| tok/s (3rd prompt, different task) | ~15 | 3.0-4.3 | ~3-4 |

**Key findings:**
- SSD streaming startup is nearly instant (0.99GB token embedding mapped initially vs full 81GB)
- Cache warms to 80-83GB after 2-3 prompts (not a persistent RAM saving after the first few queries)
- Speed is 2-5x slower and highly variable depending on which experts are in the cache
- A larger cache (60GB vs 20GB) does not meaningfully improve speed — same 3-9 tok/s range
- Context buffer and expert cache log line: "cuda SSD streaming cache budget NGB / 6.75 MiB per
  expert = M experts" — at 60GB that's 9102 experts, but model still hits SSD per new query type

**Conclusion:** SSD streaming is NOT suitable for production use on this machine. The 4-5x
average slowdown is too severe. Normal mode at 108GB / ~15 tok/s is the right config.
SSD streaming would only be useful if RAM was genuinely tight (< 15GB free), as a last resort.

**Restore plan:** When running, start ds4 via systemd normally (`sudo systemctl start ds4`).
Do NOT use --ssd-streaming for production.

## 2026-06-25 23:32 — Stage 4 launched: Nemotron-3-Super without speculative decoding

**Setup:**
- ds4 and Qwen sidekick both stopped before this stage. Nemotron occupies full 117GB unified pool.
- `deploy/nemotron-3-super/run_no_speculative.sh` ran — container `nemotron-vllm` ID 6d3e2edadd0b.
- Weights: 75GB already cached (from Benchmark 2), all 17 shards loaded in 368 seconds.
- torch.compile: 17.23s (cache hit), profiling/warmup: 16.68s, CUDA graphs: 51 PIECEWISE + 35 FULL.
- Total startup: ~435s from container launch to "Application startup complete" (17:47 → 17:55 UTC).
- Model: 69.54 GiB loaded, FP4 via Marlin kernel (GB10 has no native FP4 — expected, same as Benchmark 2).
- kv_scale warnings (FP8 attention uncalibrated): same as Benchmark 2, not an error.
- Memory after load: 117GB used, 4.0GB available.

**Smoke tests PASS:**
- 2+2 test: "4" in 51s, 0 tool calls — clean.
- File listing test: real ls output in 4m44s, 2 tool calls — tool-calling format matches correctly.
  (Note: 4m44s for a simple ls is slow. This is the model think-time cost, not a framework issue.
   Expected — Nemotron is a 120B model, tool calls take 1-3 min each at this scale without MTP.)

**Key difference from Benchmark 2:**
- `--speculative_config` removed entirely. No MTP speculative decoding.
- In Benchmark 2, MTP speculative decoding caused acceptance rate collapse at long context (0.687
  → 0.448 → 0.224 per draft position) which slowed per-token generation from fast to ~0.1 tok/s
  at 21+ tool calls. Without MTP, all generation is standard autoregressive — slower peak but
  no degradation curve.

**Hermes wildfire task launched:** 23:32 IST (epoch 1782410520).
- Command: `docker run --rm -v ~/.hermes:/opt/data nousresearch/hermes-agent chat -q "..."`
- Log: `benchmark4_qwen_sidekick/nemotron_wildfire.log`
- Workspace: `~/.hermes/wildfire_research/` (previous run moved to wildfire_research_bk2_nemotron)
- Time-box: kill at 40-45 min (23:12-23:17 UTC+5:30 = 00:12-00:17 IST) if underperforming.
- Hard deadline: task MUST end by 00:17 IST regardless of completion state.

## 2026-06-26 00:17 — Stage 4 COMPLETE (killed at 45-min deadline)

**Results:** Task killed at 2715s (45.25 min). 42 tool calls, 7 PDFs downloaded, NO final synthesis or dashboard produced.

**File audit (`benchmark4_qwen_sidekick/nemotron_wildfire_results/`, copied from `~/.hermes/wildfire_nilgiris_himalayan/`):**
| File | Size | Notes |
|------|------|-------|
| `3-6Sharma-1.pdf` | 5.5MB | Research paper (Sharma) |
| `How_20to...Prevention_20Season.pdf` | 5.8MB | Outlook Business article, forest fire prevention |
| `pdf_68a4157b8b3d38.38401489.pdf` | 875KB | Unknown source (generic hash filename) |
| `pr290426_e_743.pdf` | 145KB | Press release or report |
| `TOR-for-forest-fire-management-and-air-quality-improvement-HKH.pdf` | 1.6MB | Terms of Reference for Hindu Kush Himalayan forest fire mgmt |
| `wetlands_conservation_and_sustainable_management_in_the_nilgiris.pdf` | 660KB | Nilgiris wetlands conservation report |
| `Yojna-daily-current-affairs-eng-med-21-March-2024.pdf` | 1.4MB | Yojna magazine current affairs (light relevance) |

**Timeline:**
- 0-15 min (0-20 tool calls): Searching Zenodo API, Google Scholar, India Water Portal, ICIMOD, DuckDuckGo, CrossRef, EuropePMC — no downloads yet
- 15-35 min (20-35 tool calls): Python `requests` downloads started, 7 files acquired
- 35-45 min (35-42 tool calls): One Python download timed out at 300s, tried to install poppler-utils to read PDFs (failed, apt exit 100), still seeking more papers
- 45 min: Hard killed. Model was mid-task, no synthesis or dashboard produced.

**Comparison vs Benchmark 2 Nemotron (WITH MTP speculative decoding):**
| Metric | B2 Nemotron (MTP) | B4 Nemotron (no MTP) |
|--------|-------------------|----------------------|
| Duration | 78+ min (hit budget) | 45 min (hard killed) |
| Tool calls | 21 | 42 |
| Tool calls/min | 0.27/min | 0.93/min |
| Files downloaded | 2 PDFs | 7 PDFs |
| Final synthesis/dashboard | No (budget hit) | No (hard killed) |
| Key failure mode | MTP acceptance rate collapse | Incomplete at time limit |

**Removing MTP more than doubled tool-call throughput** (0.27 → 0.93/min). But 45 min was still not enough to complete a research task requiring ~10 downloads + synthesis + dashboard. The model spent ~25 min in pure discovery mode before first download, then got 7 files, but never reached the synthesis phase.

**Comparison vs ds4-based runs (same task):**
- Hermes+ds4 (B2 Phase 3): 79 min, 20 PDFs, dashboard produced — COMPLETED
- ds4-agent raw (B2 Phase 4): 26 min, 20 files, dashboard produced — FASTEST
- Hermes+Nemotron-3 no-MTP (B4): 45 min, 7 files, no synthesis — DID NOT COMPLETE

**Verdict:** Nemotron-3-Super-120B is not competitive with ds4-flash for agentic research tasks via Hermes, even without speculative decoding. The per-token latency at 120B scale limits tool-call throughput to ~1/min, which is too slow for a research task requiring 30-40+ tool calls before synthesis. ds4-flash at 15 tok/s with the native agent harness completes in 26 min. Nemotron at ~4-5 tok/s (estimated from smoke test timing) cannot close that gap in 45 min.

**Machine restore:**
- `sudo systemctl start ds4` — ds4 running, confirmed `/v1/models` returns deepseek-v4-flash ✓
- `sudo python3 deploy/hermes/point_at_model.py deepseek-v4-flash http://172.17.0.1:8000/v1` ✓
- All Nemotron and Hermes containers stopped ✓

## 2026-06-26 01:36 — Stage 1 Qwen3-Next-80B-A3B-Instruct-FP8 download started (new session)

**New download strategy:** Switched from HF CDN (repeated stalls) to hf-mirror.com + hfd.sh + aria2c.
- Tool: `bash /tmp/hfd.sh Qwen/Qwen3-Next-80B-A3B-Instruct-FP8 --tool aria2c -x 8 -j 2 --local-dir ~/models/Qwen3-Next-80B-FP8`
- `HF_ENDPOINT=https://hf-mirror.com` — Chinese academic mirror, different CDN from HF's XET
- Achieves 10-32 MB/s vs HF CDN's 70-80 KB/s throttled rate
- 403 errors on byte-range boundaries in aria2c log: normal (CloudFront signed URL range restrictions, internally retried), not fatal
- Model downloaded to `~/models/Qwen3-Next-80B-FP8/` (NOT inside container — host-level, then mount read-only)
- PID 2049249, log: `~/models/qwen3-next-80b-download.log`
- Completion watcher: `/tmp/completion_watcher.sh` (PID 2750365) — checks every 60s for 8 safetensors, no .aria2 temps

## 2026-06-26 03:35 — Download complete, container started

- All 8 shards complete, 77GB total on disk, no .aria2 files.
- Completion watcher fired `on_complete.sh`: stopped ds4, started `qwen-big-vllm` container.
- Container started with `--max-model-len 65536 --moe-backend marlin --enable-auto-tool-choice --tool-call-parser hermes`
- Weight loading: 75.99 GiB, 407.5s (8 shards × ~50s each — vs Nemotron's 17 shards × 54s)
- torch.compile: 35.62s (first time, not cached)
- KV cache: 31.23 GiB, 342,176 token pool
- Total startup: ~9 min (03:35 → 03:44 IST)
- Memory: 118 GiB used, 2.7 GiB available

## 2026-06-26 03:44 — Smoke tests PASS

| Test | Result | Timing |
|------|--------|--------|
| /v1/models endpoint | `qwen3-next-80b` registered, max_len=65536 | immediate |
| 2+2 arithmetic (first request) | "4" correct | 17.3s (graph compile overhead on 1st req) |
| Ocean poem (second request, 41 tokens) | Correct, fluent | 0.97s = **42.3 tok/s** |
| Tool call (ls /tmp) | `bash({'command': 'ls /tmp'})`, finish_reason=tool_calls | 0.645s |

Speed: 42-46 tok/s (3-6x faster than Nemotron-3-Super's ~4-5 tok/s). MoE effect: 80B total params but only 3B active per token.

## 2026-06-26 03:50 — Battery benchmark COMPLETE (6 tasks, port 8000)

| Task | Elapsed | Tokens | Tok/s | Quality |
|------|---------|--------|-------|---------|
| short_query | 2.4s | 106 | 44.6 | EXCELLENT (correct, no hallucinations) |
| wordsmithing | 0.5s | 16 | 33.9 | EXCELLENT |
| short_summary | 1.5s | 61 | 41.0 | EXCELLENT (complete, accurate) |
| arithmetic | 5.1s | 234 | 45.8 | EXCELLENT (correct with LaTeX formatting, concise) |
| structured_output | 1.9s | 81 | 42.2 | EXCELLENT (clean JSON, no fences) |
| translation_short | 1.7s | 73 | 44.2 | EXCELLENT (correct Hindi: "वन आग का शुरुआती पता लगाने से जीवन बचते हैं और जैव विविधता की रक्षा होती है।") |

vs Qwen3.5-2B: same speed (33-46 tok/s) but dramatically better quality — no hallucinations, correct Hindi, concise arithmetic (234 tokens vs 429).

Results saved to `benchmark4_qwen_sidekick/qwen3_next_80b_results/`.

## 2026-06-26 03:52 — First Hermes wildfire attempt FAILED: context overflow

Hermes launched with Qwen3-Next-80B on 65536 context → immediate failure:
- Hermes system prompt + conversation = ~19k tokens
- Hermes requests `max_tokens=context_length=65536` for output budget
- Total 19k + 65536 > 65536 → HTTP 400 from vLLM
- Root cause: Hermes calculates `max_tokens = context_length - used_tokens` but also requests `max_tokens = context_length` for the first call. Known behavior — requires context_length >> Hermes system prompt size.

**Fix:** Restart vLLM with `--max-model-len 131072`. This model is a Mamba-hybrid (Qwen3Next): 
most layers are Mamba SSM (O(1) state-based memory, NOT in KV cache). Only the attention layers 
need KV cache. Result: KV cache barely changes with context length increase.

## 2026-06-26 04:03 — Container restarted with 131072 context, wildfire task started

- vLLM restarted: `--max-model-len 131072`
- Weight reload: same timing (~407s, 7 min)
- KV cache at 131072: **31.36 GiB** (vs 31.23 GiB at 65536) — virtually identical, confirms Mamba-hybrid
- KV token pool: 342,176 tokens — ample headroom
- `deploy/qwen3-next-80b/run.sh` updated: `--max-model-len 131072`
- Hermes pointed at qwen3-next-80b: `sudo python3 deploy/hermes/point_at_model.py qwen3-next-80b http://172.17.0.1:8000/v1` ✓
- Wildfire task launched: `docker run --rm -v ~/.hermes:/opt/data --network host nousresearch/hermes-agent chat -q "Research wildfire risk interventions..."`
- Start time: 04:03:52 IST (epoch 1782426832)
- PID 3074174, log: `benchmark4_qwen_sidekick/qwen3_next_80b_wildfire.log`
- 45-min killer PID 3074177 fires at ~04:48:52 IST
- Initial activity: mkdir attempts (1 fail /opt/hermes, 1 success /opt/data/wildfire_research) then Zenodo browse starting — model already showing faster recovery than Nemotron
- IN PROGRESS as of this checkpoint entry

## 2026-06-26 04:03 — Hermes wildfire task v2-v6: context overflow saga

**Root cause of all context failures:** Qwen3-Next-80B tokenizes ~46% MORE tokens than Hermes estimates (~4 chars/token assumed, actual closer to 2.7 chars/token for this model). Hermes estimates "safe" context and requests max_tokens = (context_length - estimated_used). But actual tokens > estimated, so 65536_output + 65537_actual_input > 131072.

**Hermes v2 (max-model-len=131072):** 58 tool calls in 6m42s, context overflow at 44k estimated (65k actual). Used browser_navigate exclusively → large HTML → rapid context fill. 0 files.

**Hermes v3 (131072, reasoning_effort=low, environment_hint bash):** 62 tool calls in 4m45s, still browser-heavy. 5 files downloaded. Same context overflow.

**Hermes v4 (131072, env_hint explicit no-web_search/arxiv):** Model used curl correctly (curl https://zenodo.org/api/records?... → compact JSON). 5 files in 4m45s before overflow:
- parvati_valley_fire_study.pdf (Zenodo, Himachal Pradesh)
- himalaya_fire_emissions.zip (Zenodo)
- himalaya_climate_fire_data.zip (Zenodo)
- himalaya_climate_fire_readme.md
- nilgiri_langur_studbook.pdf (WII)
Saved to `benchmark4_qwen_sidekick/qwen3_next_80b_wildfire_v4_partial/`.

**Hermes v5 (max-model-len=262144, KV cache 30.38 GiB = 331k tokens):** Killed at 4 min by stale v4 killer process (bug). Model discovered execute_code (🐍) tool on its own.

**Hermes v6 (262144, stale killers purged):** Model found existing Benchmark 2 ds4 run artifacts at /opt/data/wildfire_research_ds4_run/. Read the existing dashboard, verified 3 DOI links, produced complete synthesis. COMPLETED in ~1 min, naturally exited.
- Synthesis: 5 key disagreements, 10 measurement metrics, research gaps identified, all 20 B2 papers cited
- Saved to `benchmark4_qwen_sidekick/qwen3_next_80b_wildfire_v6_synthesis/`
- NOT an independent fresh-start: relied on B2's pre-downloaded corpus
- Intelligent context reuse — but doesn't qualify as a fresh agentic research run

**Context overflow root cause (definitive):** Hermes's token estimator assumes ~4 chars/token. Qwen3-Next tokenizes at ~2.7 chars/token (BPE-heavy tokenizer). Even at 262k max_model_len, the estimated "safe" budget is ~46% too optimistic. Hermes would need max_model_len ≈ 400k+ for a true independent 60-turn research session.

**Machine restored:**
- `sudo systemctl start ds4` → deepseek-v4-flash on port 8000 ✓
- `sudo python3 deploy/hermes/point_at_model.py deepseek-v4-flash http://172.17.0.1:8000/v1` ✓
- docker stop qwen-big-vllm ✓
