# Benchmark 4 Report: Qwen3.5-2B Sidekick, SSD Streaming, Nemotron Retry

**Machine:** DGX Spark GB10, 121.63GiB unified CPU/GPU memory, arm64  
**Date:** 2026-06-25 to 2026-06-26  
**Four stages, completed in sequence.**

---

## Stage 1: Qwen3-Next-80B-A3B-Instruct-FP8 (COMPLETE — deferred and retried)

**Outcome: Download succeeded via hf-mirror.com + aria2c. Smoke tests PASS. Battery EXCELLENT. Hermes agentic task hit context overflow; partial fresh-run results captured.**

### Download

Prior session download stalled using HF CDN. Retry using `hf-mirror.com` + `hfd.sh` + aria2c:
- `HF_ENDPOINT=https://hf-mirror.com bash /tmp/hfd.sh Qwen/Qwen3-Next-80B-A3B-Instruct-FP8 --tool aria2c -x 8 -j 2 --local-dir ~/models/Qwen3-Next-80B-FP8`
- 10-32 MB/s sustained vs HF CDN's 70-80 KB/s throttled rate
- 8 shards, 77GB total, completed in ~2h from cold start
- 403 errors in aria2c log are internal retries on CloudFront byte-range limits — not fatal

### Setup

- `deploy/qwen3-next-80b/run.sh` mounts `~/models/Qwen3-Next-80B-FP8:/model:ro`
- Required flag: `--moe-backend marlin` (FP8 block-quant; FLASHINFER_CUTLASS kernel doesn't support this checkpoint)
- Final context window: `--max-model-len 262144` (iterated up from 65536 — see Hermes section)
- Architecture: Qwen3NextForCausalLM — Mamba-hybrid SSM + attention. KV cache barely changes with context length (Mamba layers use O(1) state memory, not KV cache)
- Weight load: 75.99 GiB, 407s. torch.compile: 35.62s. KV cache: 31.36 GiB = 342,176 token pool
- Total startup: ~9 min

### Memory

| Config | Used | Available | KV Cache |
|--------|------|-----------|----------|
| qwen-big-vllm alone | 118 GiB | 2.7 GiB | 31.36 GiB |
| At 65536 max_model_len | 118 GiB | 2.7 GiB | 31.23 GiB |
| At 131072 max_model_len | 118 GiB | 2.7 GiB | 31.36 GiB |
| At 262144 max_model_len | 118 GiB | 2.7 GiB | 30.38 GiB |

KV cache ~constant at all context lengths — confirms Mamba-hybrid: few attention layers need KV.

### Smoke Tests

| Test | Result | Timing |
|------|--------|--------|
| /v1/models | `qwen3-next-80b`, max_len=262144 | immediate |
| 2+2 (first request) | "4" correct | 17.3s (CUDA graph compile overhead) |
| Ocean poem (second request, 41 tokens) | Correct, fluent | 0.97s = **42.3 tok/s** |
| Tool call (ls /tmp) | `bash({'command': 'ls /tmp'})`, finish_reason=tool_calls | 0.645s |

**42-46 tok/s** — 3x faster than ds4-flash (15 tok/s), 9x faster than Nemotron-3-Super (~4-5 tok/s). MoE effect: 80B total params, only 3B active per token.

### Battery Benchmark (6 tasks, same prompts as Stage 2 sidekick)

| Task | Elapsed | Tokens | Tok/s | Quality |
|------|---------|--------|-------|---------|
| short_query | 2.4s | 106 | 44.6 | **EXCELLENT** (correct, no hallucinations — vs POOR for 2B) |
| wordsmithing | 0.5s | 16 | 33.9 | **EXCELLENT** |
| short_summary | 1.5s | 61 | 41.0 | **EXCELLENT** |
| arithmetic | 5.1s | 234 | 45.8 | **EXCELLENT** (concise, LaTeX formatting, correct — vs 429 tokens for 2B) |
| structured_output | 1.9s | 81 | 42.2 | **EXCELLENT** (clean JSON, no markdown fences) |
| translation_short | 1.7s | 73 | 44.2 | **EXCELLENT** (correct Hindi — vs garbled for 2B) |

Same speed as Qwen3.5-2B (33-46 tok/s) but dramatically better quality on every task.

### Hermes Agentic Task (Wildfire Research — same prompt as all prior runs)

**Context overflow root cause:** Hermes estimates tokens using ~4 chars/token. Qwen3-Next's BPE tokenizer produces ~2.7 chars/token actual — 46% more tokens than estimated. Hermes's max_tokens calculation exceeds available context, causing HTTP 400 from vLLM.

**Run history:**

| Run | max_model_len | Duration | Tool calls | Files | Outcome |
|-----|--------------|----------|-----------|-------|---------|
| v2 | 131072 | 6m42s | 58 | 0 | Context overflow (browser HTML) |
| v3 | 131072 | 4m45s | 62 | 5 | Context overflow (partial, curl-based) |
| v4 | 131072 | 4m45s | 62 | 5 | Context overflow — 5 Zenodo datasets/PDFs saved |
| v5 | 262144 | 4m | ~30 | 0 | Killed early by stale v4 killer process (bug) |
| v6 | 262144 | ~1m | ~10 | 0 new | **COMPLETED** synthesis by reading B2 ds4 corpus |

**v4 downloads (5 files, fresh-start):**
- `parvati_valley_fire_study.pdf` — Zenodo, Himachal Pradesh wildfire impacts (14KB)
- `himalaya_fire_emissions.zip` — Zenodo CH4 fire emissions dataset (7.3MB)
- `himalaya_climate_fire_data.zip` — Zenodo Himalayas 2013-2023 climate-fire data (17MB)
- `himalaya_climate_fire_readme.md` — Dataset documentation
- `nilgiri_langur_studbook.pdf` — WII (marginal relevance)

**v6 synthesis (completed — builds on B2 corpus):** Read B2 ds4 dashboard (20 papers), verified DOIs, produced full synthesis. 5 key disagreements, 10 measurement metrics, research gaps. NOT an independent fresh-start — relied on B2's pre-downloaded corpus.

**Key finding:** Qwen3-Next at 44 tok/s generates tool calls ~9x faster than Nemotron-3-Super. For browser-based research this causes rapid context bloat; for curl-based API access it gets to downloads in under 5 minutes. A dedicated Hermes context window ≥400k tokens would be needed for an independent 60-turn session, which doesn't fit on GB10's KV cache budget.

### Verdict

Qwen3-Next-80B-A3B-FP8 is the **strongest model tested** for ds4 replacement:
- Same decode speed as Qwen3.5-2B (44 tok/s) despite 40x more parameters — MoE efficiency
- Far better quality than 2B on every task dimension
- 3x faster than ds4-flash — would complete wildfire task faster if context didn't overflow
- Mamba-hybrid enables enormous context without KV cache penalty (262k fits in same 31 GiB)
- **Blocking issue for Hermes agentic tasks:** tokenizer vs Hermes estimator mismatch causes systematic context overflow. Workaround requires either custom Hermes tokenizer config or model-aware context budget.

---

## Stage 2: ds4-flash + Qwen3.5-2B Sidekick (COMPLETE)

### Setup

- ds4: normal mode, port 8000, ~108GB unified CUDA memory
- Qwen3.5-2B via `vllm/vllm-openai:cu130-nightly`, port 8001
- Critical setting: `--gpu-memory-utilization 0.08` (9.73GB budget, fits in 10.58GB free after ds4)
  - 0.09 fails: "Free memory 10.58/121.63 GiB < desired 10.95 GiB" (only 37MB headroom)
- Sidekick startup: ~99s (model load 20s + torch.compile 20s + profiling/warmup 34s + graphs 1s)
- Combined memory: 118GB used, 3.3GB available — tight but stable

### Battery Test Results (6 short tasks, sequential, port 8001)

| Task | Elapsed | Tokens | Speed | Quality |
|------|---------|--------|-------|---------|
| short_query | 2.1s | 96 | 44.7 tok/s | POOR (hallucinations: "borignè", "mothwood") |
| wordsmithing | 0.5s | 22 | 41.6 tok/s | GOOD |
| short_summary | 1.3s | 43 | 32.8 tok/s | EXCELLENT |
| arithmetic | 9.4s | 429 | 45.8 tok/s | GOOD (verbose but correct) |
| structured_output | 2.0s | 90 | 44.7 tok/s | EXCELLENT (clean JSON) |
| translation_short | 3.5s | 158 | 45.2 tok/s | POOR (garbled Hindi, mixed scripts) |

### Concurrent Test (ds4 + sidekick simultaneously)

| Metric | Solo | Concurrent | Change |
|--------|------|------------|--------|
| ds4 tok/s | ~15 | 6.6 | -56% |
| sidekick tok/s | ~44.7 | 20.8 | -53% |
| Wall time | — | 18.1s | — |

~50% mutual slowdown from memory bandwidth contention on the GB10 unified pool.
No OOM, no crashes — concurrent operation is feasible but degrades both endpoints.

### Verdict

- Qwen3.5-2B fits (barely — 3.3GB margin) without OOM
- Speed: 33-46 tok/s for short sequential tasks; drops to ~21 tok/s under concurrency
- Quality: excellent for formatting/extraction tasks; too small for factual knowledge or non-English
- Concurrent routing causes ~50% slowdown for both endpoints — sequential routing preferred
- **Recommended use:** Low-stakes formatting, JSON extraction, short summaries. Route traffic sequentially, not simultaneously with ds4.

---

## Stage 3: ds4 SSD Streaming (COMPLETE)

### Setup

Normal ds4 stopped. Ran `ds4-server` with `--ssd-streaming --ssd-streaming-cache-experts NGB`.
Tested 20GB and 60GB expert caches.

### Results

| Metric | Normal mode | SSD 20GB cache | SSD 60GB cache |
|--------|-------------|----------------|----------------|
| RAM at startup | 108GB | 13GB | 13GB |
| RAM after 2-3 prompts | 108GB | 81GB | 83GB |
| Startup time | ~2 min | < 1 sec | < 1 sec |
| tok/s (1st prompt) | ~15 | 3.1-3.4 | 3.1 |
| tok/s (2nd prompt, warmed) | ~15 | 8.5 | ~8-9 |
| tok/s (3rd prompt, different task) | ~15 | 3.0-4.3 | ~3-4 |

### Key Findings

- Startup is nearly instant (only 0.99GB token embedding mapped initially)
- Cache warms to 80-83GB after 2-3 prompts — no persistent RAM saving after warmup
- Speed: 2-5x slower, highly variable (depends on expert cache hit rate)
- Larger cache (60GB vs 20GB) does not meaningfully improve speed
- **Not suitable for production.** Use only if RAM genuinely below 15GB (not the case here).

---

## Stage 4: Nemotron-3-Super-120B without Speculative Decoding (COMPLETE, time-boxed)

### Background

Benchmark 2 Phase 10 ran Nemotron-3-Super-120B-A12B-NVFP4 via Hermes with MTP speculative
decoding enabled. The run failed to complete: MTP acceptance rate collapsed at long context
(0.687 → 0.448 → 0.224 per draft position), reducing per-token generation to ~0.1 tok/s after
21+ tool calls.

Stage 4 hypothesis: removing MTP speculative decoding eliminates the degradation curve.

### Setup

- `deploy/nemotron-3-super/run_no_speculative.sh` — `--speculative_config` removed entirely
- 75GB weights from Benchmark 2 cache (no re-download needed)
- Startup: 17 shards × ~24s = 368s weight load, torch.compile 17.23s, warmup 16.68s
- Total startup: ~435s to "Application startup complete"
- Memory: 117GB used, 4.0GB available (FP4 via Marlin kernel — GB10 has no native FP4)

### Smoke Tests

| Test | Result | Timing |
|------|--------|--------|
| 2+2 arithmetic | "4" (correct) | 51s, 0 tool calls |
| List files (tool use) | Correct real ls output | 4m44s, 2 tool calls |

Note: 4m44s for a simple tool call reflects per-token latency at 120B scale (~4-5 tok/s
estimated), not a framework issue.

### Wildfire Research Task (same prompt as Benchmark 2)

Hermes container launched with identical wildfire research prompt at 23:32 IST. Hard killed at 45 min.

**Files downloaded (7 PDFs, 16MB total):**

| File | Size |
|------|------|
| `3-6Sharma-1.pdf` | 5.5MB |
| `How_20to_20Turn_20the_20Forest_20Fire_20Season_20...pdf` | 5.8MB |
| `pdf_68a4157b8b3d38.38401489.pdf` | 875KB |
| `pr290426_e_743.pdf` | 145KB |
| `TOR-for-forest-fire-management-and-air-quality-improvement-HKH.pdf` | 1.6MB |
| `wetlands_conservation_and_sustainable_management_in_the_nilgiris.pdf` | 660KB |
| `Yojna-daily-current-affairs-eng-med-21-March-2024.pdf` | 1.4MB |

Copied to `benchmark4_qwen_sidekick/nemotron_wildfire_results/`.

**Timeline:**
- 0-25 min: Pure discovery (Zenodo API, CrossRef, EuropePMC, ICIMOD, Google Scholar, DuckDuckGo)
- 25-35 min: Python `requests` downloads — 7 files acquired
- 35-45 min: One download timed out at 300s; tried `poppler-utils` for PDF reading (apt failed);
  killed mid-task
- **No final synthesis or dashboard produced.**

### Comparison: MTP vs No-MTP vs ds4

| Metric | B2 Nemotron (MTP) | B4 Nemotron (no MTP) | B2 Hermes+ds4 | B2 ds4-agent |
|--------|-------------------|-----------------------|----------------|--------------|
| Total time | 78+ min | 45 min (killed) | 79 min | 26 min |
| Tool calls | 21 | 42 | 40 | ~20 |
| Tool calls/min | 0.27 | 0.93 | 0.51 | ~0.77 |
| Files downloaded | 2 PDFs | 7 PDFs | 20 PDFs | 20 files |
| Synthesis/dashboard | No | No | Yes | Yes |
| Completed | No | No | Yes | Yes |

### Verdict

Removing MTP **more than tripled tool-call throughput** (0.27 → 0.93/min). Nemotron got 7 files
vs 2 from the MTP run — a clear improvement.

However, **45 min was still insufficient to complete the task.** The model spent 25 of 45 minutes
in pure discovery/search mode before downloading a single file. Per-token latency at 120B scale
(~4-5 tok/s estimated, vs ds4's ~15 tok/s) is the hard constraint: even at 1 tool call/min
cadence, a research task requiring 30-40 tool calls + synthesis takes 50-70+ minutes minimum.

ds4-flash (7B-equivalent MoE architecture, 15 tok/s) completes the same task in 26 min with
the native agent harness. **Nemotron-3-Super is not competitive for agentic research tasks on
this hardware** unless per-call latency can be substantially reduced.

---

## Head-to-Head: ds4-flash vs Qwen3-Next-80B (Hermes, fresh-start)

**Date:** 2026-06-26  
**Task:** Identical wildfire research prompt from Benchmark 2 (Nilgiris + Himalayan region).  
**Conditions:** Fresh workspace (all prior wildfire dirs archived), both models routed through
`hermes-token-proxy` on `:8001`, 90-minute hard time limit per run. ds4 first, then Qwen.  
**Infrastructure fix:** `deploy/hermes/token_proxy.py` (proxy) applied `max_tokens / 1.46`
correction for `qwen3-next-80b`, preventing the context overflow that blocked all prior attempts.

### Results

| Metric | ds4-flash | Qwen3-Next-80B |
|--------|-----------|----------------|
| Time | 82 min | 4.5 min |
| Tool calls | ~60+ (estimated from transcript) | 18 |
| PDFs downloaded | **7** (real papers) | **0** |
| Dashboard produced | **YES** (21KB, 28 papers, 6 disagreements) | No |
| Synthesis quality | Real evidence, real citations, OpenAlex-sourced | Parametric only — ICFRE/ICIMOD from training data |
| Completed task | **YES** — natural exit | **NO** — early abandonment |
| Proxy corrections fired | 0 (ds4 tokenizer matches Hermes estimator) | 10 (65536 → 44887 each time) |

### What happened: ds4

ds4 wrote a persistent Python script (`search_papers.py`) using `urllib.request` + OpenAlex API.
Over 82 minutes it:
- Queried OpenAlex for 65 papers, filtered to 28 key papers with DOIs
- Downloaded 7 full-text PDFs (Zenodo + open-access URLs)
- Survived one context compression event (compression summary failed, fallback marker inserted,
  run continued without interruption)
- Produced `dashboard.html` with: 7 interventions with evidence ratings, 6 identified
  disagreements in the literature, 5 measurement priority tiers, full paper list with DOIs

Saved to `~/.hermes/home/wildfire-research/` (model chose this path, not `wildfire_research/`).
Copied to `head_to_head_ds4/wildfire_research/`.

**Disagreements identified (ds4):**
1. Fire trend in Nilgiris: declining (2018 paper) vs increasing (2021) — different sensors/windows
2. Prescribed burning: beneficial in Uttarakhand chir pine vs. degrading in Western Ghats — different forest types
3. Fire-Lantana cycle: classic theory (fire promotes Lantana) vs. new finding (Lantana suppresses fire in shola)
4. Community participation: effective vs. underfunded governance failures
5. Primary driver: anthropogenic ignitions vs. meteorological extremes
6. GIS model transferability: models trained in one region may not transfer

### What happened: Qwen3-Next-80B

The proxy fix worked — no context overflow. But the model hit a different failure:
- Step 1: `curl ... | jq` — jq not installed
- Step 2: `sudo apt-get install jq` — no sudo in container, timed out (45s)
- Step 3: Switched to Python `requests` — SSL certificate errors on Zenodo and NGO sites
- Step 4: After ~6 attempts with SSL errors, gave up on downloading and synthesized from training data

Output (`analysis.md`, 9.8KB): cites ICFRE 2019, ICIMOD 2021, MoEFCC 1988, WII, FSI — all
real institutions, but citations come from parametric knowledge, not downloaded documents.
Task was not completed as specified ("find and download roughly 10 relevant papers").

The proxy fired 10 times (`max_tokens: 65536 → 44887`) confirming context overhead was minimal
(session stayed well under the corrected budget). Failure was agent behavior, not context overflow.

### Root cause analysis: why ds4 succeeded and Qwen3-Next did not

This is NOT a pure model capability difference. ds4 used `urllib.request` (stdlib, no SSL issues
in this container); Qwen used `requests` (which has stricter SSL cert verification and hit
certificate errors on some government/NGO sites). The environments were identical but the models
chose different HTTP libraries with different failure modes.

ds4 also showed stronger error-recovery behavior: when one API or URL failed, it tried another.
Qwen switched strategies twice, hit errors both times, then concluded "I can't download files
due to SSL issues" and synthesized from knowledge.

**This failure mode is fixable with a better `environment_hint`.** Adding:
> *"If SSL certificate errors occur, use `urllib.request` with an SSL context that sets
> `check_hostname=False, verify_mode=CERT_NONE`, or pass `--insecure` to curl."*

would likely prevent the abandonment. The proxy fix for context overflow is confirmed working;
agent behavioral hints are the remaining gap.

### Security audit (post-benchmark)

| Check | Result |
|-------|--------|
| New system packages | CLEAN |
| New Hermes skills/hooks | CLEAN |
| New cron entries | CLEAN |
| Python packages via uv | CLEAN (uv cache dir created, no packages installed) |
| Files written to ~/.hermes/ | Research files only (PDFs, JSON, dashboard, search script) |
| Lingering processes | None after benchmark script exited |
| Lingering containers | None (hermes --rm, qwen-big-vllm stopped by benchmark script) |

The ds4 model created `search_papers.py` (a research helper script) — inspected, contains
only OpenAlex/Zenodo API calls and file writes. No network callbacks, no credential exfiltration,
no persistence mechanisms outside `~/.hermes/home/wildfire-research/`.

### Verdict

**For agentic research tasks on this hardware: ds4-flash remains the recommended model.**

| | ds4-flash | Qwen3-Next-80B |
|---|---|---|
| Agentic completion | Reliable (2/2 runs completed) | Failed on fresh-start (0/2 fresh runs completed) |
| Speed | 15 tok/s | 44 tok/s (3x faster, irrelevant if task doesn't complete) |
| Context | 100k, works with Hermes | 262k, proxy required, SSL behavior caused abandonment |
| Quality (battery) | Good | EXCELLENT (all 6 tasks) |
| Recommendation | **Use for Hermes agentic tasks** | Use for single-turn, high-quality outputs |

Qwen3-Next-80B's 3x speed advantage is real and useful for single-turn or short-session tasks
(translation, summarization, structured extraction — all EXCELLENT in battery tests). But for
multi-step research requiring real downloads and error recovery, ds4's more persistent tool-use
behavior currently wins.

The remaining path to making Qwen3-Next-80B competitive for agentic tasks: fix the SSL
abandonment via `environment_hint`, then rerun. The context overflow is solved.

---

## Head-to-Head v2: Qwen3-Next-80B with hermes-agent-local (FAILED)

**Date:** 2026-06-26  
**Goal:** Rerun Qwen with improved container (`hermes-agent-local`: jq, wget, sudo) and updated
`environment_hint` to see if SSL failure from v1 could be avoided.  
**Hypothesis:** v1 failed due to SSL cert issues in `requests`; v2 with jq/wget/sudo available and
hint to prefer `urllib.request` should reach downloads.

### What actually happened

Qwen spent **all 120 iterations** (`agent.max_turns: 120`) doing the same thing in a loop:

```bash
curl -s "https://www.google.com/search?q=Wildfire+risk+..." | grep -o "https://[^[:space:]]*\.pdf" | head -5
```

Google returns JavaScript-heavy HTML to curl — no PDF links are extracted. The model saw empty
output each time, said "I'm having difficulty retrieving links, let me try a different search
term", and issued the same command with slightly different keywords. This repeated from line 50 to
line 768 of the transcript — 118 consecutive search attempts, all empty, all ignored.

The model never tried:
- `browser_navigate` (despite hint saying browser is available for JS-rendered pages)
- `execute_code` / Python (despite hint saying to prefer `urllib.request`)
- Zenodo API (`export.zenodo.org`) or CrossRef or OpenAlex — approaches ds4 used successfully
- `wget` or any other download tool
- The one `arxiv.org` API attempt (line 215) was blocked by Hermes's 60s command timeout

At iteration 120 Hermes auto-requested a summary. The model acknowledged it had downloaded nothing:

> *"I've been unable to successfully retrieve direct links to PDF publications through web
> searches. Despite extensive efforts across multiple search strategies targeting government
> reports, academic publications, and NGO documents, I haven't been able to download the
> requested 10+ papers and reports due to limitations in accessing direct PDF links through
> web scraping methods."*

The run ended at 10m19s, 243 messages (2 user + 240 tool calls + summary), zero files produced.

### Results

| Metric | Qwen v1 (head-to-head) | Qwen v2 (hermes-agent-local) |
|--------|------------------------|------------------------------|
| Container | upstream `nousresearch/hermes-agent` | `hermes-agent-local` (jq, wget, sudo) |
| Duration | 4.5 min | 10m19s |
| Iterations used | 18 | 120 (budget exhausted) |
| Files downloaded | 0 | 0 |
| Synthesis produced | `analysis.md` (parametric, no real downloads) | Nothing |
| Strategy | curl → Python requests → SSL error → gave up | curl google.com × 120 → iteration limit |

**v2 is strictly worse than v1.** v1 at least reached Python and produced a synthesis from
parametric knowledge. v2 never got past curl-google-search.

### Integrity note: the "7 PDFs" in the run script summary was wrong

The `run_qwen_v2.sh` script collected from two paths post-run:
```bash
sudo cp -r /home/beeps/.hermes/wildfire_research "$RESULTS/wildfire_research"
sudo cp -r /home/beeps/.hermes/home/wildfire-research "$RESULTS/wildfire_research_home"
```

The script archived `~/.hermes/wildfire_research` before the run, but **NOT**
`~/.hermes/home/wildfire-research`. That directory contained ds4's files from the earlier
head-to-head run. The post-run comparison `QWEN_PDFS=7` came from counting those ds4 files —
not from anything Qwen produced. The script's comparison table was misleading.

Qwen v2 produced zero files. All 7 PDFs shown in the terminal summary were ds4's output.

### Why v2 was worse than v1

In v1, Qwen used Python `requests` (even though it then hit SSL errors). In v2, the
`environment_hint` was updated to say "Prefer urllib.request over requests". The model may have
avoided Python entirely precisely because the hint made `requests` sound problematic — but then
didn't pivot to `urllib.request` or the browser either. Instead it fell back to bash `curl`
against Google Search, which is a broken strategy the model repeated until iteration exhaustion.

The hint exposed a model behavior issue: when the primary approach is flagged as problematic
without a clear working alternative being demonstrated concretely, Qwen3-Next-80B appears to
revert to a naive fallback loop rather than exploring the available tool set.

### What would be needed to fix Qwen for this task

1. **Environment hint must be more directive.** Instead of "prefer urllib.request", provide a
   working Python template showing how to call Zenodo/OpenAlex/CrossRef APIs directly.
2. **Zenodo and OpenAlex should be listed as explicit search strategies** — these are the APIs
   ds4 used successfully. Google search via curl is an obvious-but-wrong strategy.
3. **Browser hint needs explicit trigger.** "Use browser_navigate for JS-rendered pages" is too
   passive; the model should be told "If curl returns empty HTML, switch to browser_navigate
   immediately."

These are all `environment_hint` changes — no code, no image changes needed.

### Verdict (updated)

**Qwen3-Next-80B is not ready for agentic research tasks via Hermes.** Both fresh-start attempts
have failed, for different reasons. The context overflow from Stage 1 is fixed (proxy works). The
remaining gap is agent-level reasoning under tool-use constraints: Qwen appears to get stuck in
low-entropy search loops without self-correcting, whereas ds4 tries multiple distinct strategies
(OpenAlex API, CrossRef, direct Zenodo, fallback to curl) before conceding.

**ds4-flash remains the recommended model for Hermes agentic tasks** until Qwen's environment
hint can be rewritten with concrete working code examples.

---

## Overall Findings

### Memory and Configuration

| Config | RAM used | Available | OOM risk |
|--------|----------|-----------|----------|
| ds4 alone (normal) | 108GB | 13GB | None |
| ds4 + Qwen3.5-2B sidekick | 118GB | 3.3GB | Low (tight) |
| ds4 SSD streaming (warmed) | 81-83GB | ~38GB | None |
| Nemotron-3-Super (NVFP4) | 117GB | 4GB | None |

### Speed Summary

| Model | Mode | tok/s |
|-------|------|-------|
| ds4-flash | normal | ~15 |
| ds4-flash | SSD streaming (20GB cache, cold) | 3.1-3.4 |
| ds4-flash | SSD streaming (20GB cache, warm) | 8.5 |
| Qwen3.5-2B sidekick | sequential | 33-46 |
| Qwen3.5-2B sidekick | concurrent with ds4 | ~21 |
| Nemotron-3-Super (no MTP) | ~4-5 (estimated from smoke test) | |

### Recommendations

1. **Default config:** ds4 alone, normal mode (`sudo systemctl start ds4`). Best balance of
   speed (15 tok/s), quality, and stability.

2. **Sidekick config:** Add Qwen3.5-2B on port 8001 only for light formatting/extraction tasks
   where ds4 throughput matters more than sidekick latency. Route sequentially — avoid
   simultaneous queries to both endpoints.

3. **SSD streaming:** Do NOT use in production. 3-9 tok/s (vs 15 tok/s) with no persistent
   RAM saving after warmup. Only relevant if available RAM drops below ~15GB, which requires
   another large model running simultaneously.

4. **Nemotron-3-Super:** Not recommended for agentic tasks via Hermes on this hardware. Per-token
   latency at 120B scale is too high for the tool-call cadence research tasks require. Would
   need either (a) a faster serving path than vLLM on GB10, (b) a shorter/simpler task, or
   (c) significantly lower latency model to pair with Hermes instead.
