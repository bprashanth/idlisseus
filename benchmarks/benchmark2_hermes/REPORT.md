# Benchmark 2: Hermes Agent vs raw ds4-agent, ds4 vs Nemotron-3-Super

Three-way comparison on one open-ended, genuinely agentic task — research wildfire-risk
interventions for the Nilgiris/Himalayan region, find and download the literature yourself
(no pre-given corpus, no URLs), answer with evidence, disagreements, recommended measurements,
a dashboard, and citations. Full plan and phase-by-phase log in `PLAN.md` and `CHECKPOINT.md`.

## The three conditions

| Condition | Harness | Model | Result |
|---|---|---|---|
| ds4 (raw `ds4-agent`) | Native, ships with ds4 | DeepSeek V4 Flash, q2-imatrix | **Completed.** 25min, 20 PDFs, full answer + dashboard |
| Hermes + ds4 | Hermes Agent (NousResearch) | DeepSeek V4 Flash, q2-imatrix | **Completed.** 79min, 20 PDFs, full answer + dashboard |
| Hermes + Nemotron-3 | Hermes Agent | Nemotron-3-Super-120B, NVFP4 via vLLM | **Did not complete.** Hit its 60-turn budget after 1h52m, 2 PDFs, no answer/dashboard produced |

No raw-Nemotron-3 condition, per direction — Nemotron-3 ships no equivalent to `ds4-agent` (no
built-in multi-step tool-use harness of its own), so there's nothing meaningful to run "raw."

## ds4 (raw `ds4-agent`) — the strongest result

25 minutes, 20 real PDFs (28MB) from Zenodo/Crossref, **zero command timeouts or tool-call
friction**, a working (if CDN-linked, not fully offline) HTML dashboard, and an answer that cited
specific named papers and authors per claim ("Maurya et al. 2022", "Sreelakshmi & Anil 2026") and
explicitly flagged a real gap ("no Nilgiris-specific paper was found on Zenodo"). This is the
fastest, most reliable, and arguably most specific of the three results — on a model that costs
nothing per token and runs entirely on this machine.

## Hermes + ds4 — works, but the harness adds real friction

Same model, swapped harness: 79 minutes (3x slower than raw ds4-agent), still 20 PDFs (78MB,
larger/heavier sources than ds4-agent picked), citations verified accurate against the actual
downloaded filenames (no fabrication found). But ~12 of its tool calls hit a 60-second
timeout-denial before succeeding, and the session needed context compaction twice. *(Caveat: the
tool-call denominator used to compute a "30%" friction rate earlier in this run was later found to
be undercounted — see "things that went wrong" below — so the 12 timeout occurrences are a solid
count, but the percentage of total tool calls they represent is not reliable. The qualitative
finding stands: Hermes adds real, measurable friction on top of the same model ds4-agent ran
cleanly.)*

## Hermes + Nemotron-3 — the model is real, the combination did not work on this hardware

This is the most important finding of the round, and it's decisive, not ambiguous:

- **Setup worked.** Nemotron-3-Super-120B (NVFP4, vLLM, NVIDIA's own DGX Spark cookbook) loaded
  and served correctly, passed both the direct API smoke test and the Hermes tool-calling smoke
  test (2 tool calls, 40s, correct file listing — actually *more* tool-call-efficient than Hermes+
  ds4's equivalent smoke test).
- **The actual task did not work.** Given the real wildfire research task, Hermes+Nemotron-3 ran
  for 1 hour 52 minutes and 118 tool calls — then hit its own configured 60-turn iteration budget
  and stopped, having saved only 2 of an intended ~10-20 papers and produced **no final answer, no
  dashboard, no citations**. Its last logged action was a Python traceback.
- **Root cause is confirmed, not assumed.** Per-token latency degraded severely as the
  conversation context grew across tool calls. This was checked directly, not inferred: `nvidia-
  smi` showed 96% sustained GPU utilization throughout (the engine was genuinely computing, not
  hung/deadlocked), and vLLM's own logged metrics showed the MTP speculative-decoding
  per-position acceptance rate collapsing at longer context (0.687 → 0.448 → 0.224 across draft
  positions in one sample) — meaning the speculative-decoding speedup this config relies on stops
  working as the agentic session's context grows, and per-token latency degrades accordingly. A
  direct test request late in the session took 50 seconds to produce 5 tokens.
- This is a property of *this specific serving configuration* (NVFP4 + MTP speculative decoding +
  long accumulating agentic context) on *this hardware*, not necessarily a property of the model
  itself under a different serving setup (e.g. without speculative decoding, or with a context-
  length-aware re-tuning of `num_speculative_tokens`).

## Other things found along the way, worth keeping on record

- **Nemotron-3 self-identification oddity.** Asked directly "what model are you," it answered "I'm
  ChatGPT, a large language model trained by NVIDIA" — and its own reasoning trace claimed a
  system prompt told it this, though no system message was sent. Likely a training-data
  contamination/distillation artifact, not a serving misconfiguration. Doesn't affect tool-use
  capability but is a real correctness oddity.
- **Download stalled once, recovered cleanly.** During the ~76GB Nemotron-3 weights download, 2 of
  16 safetensor shards stalled for over an hour (confirmed via `.incomplete` file mtimes showing
  zero growth while other shards completed around them) while the container stayed "Up." Fixed by
  restarting the container — `huggingface_hub` re-fetched just the 2 stuck blobs, not the ~67GB
  already complete. Worth treating as a known risk for this vLLM-nightly + HF-downloader
  combination on this network, not a one-off fluke — `PLAN_MODEL.md` now documents the detection
  method (cache-dir growth + `.incomplete` mtime check) for future model trials.
- **NVIDIA's own example config has a latent correctness risk.** `--max-model-len 1000000` only
  works via `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1`, overriding the model's actual trained
  `max_position_embeddings` of 262,144 — vLLM's own startup warning says positions beyond that can
  produce NaN output (if RoPE-based) or CUDA out-of-bounds errors. Our task never came close to
  262K tokens in a single request, so this almost certainly didn't bite here, but it's a real
  caveat in the guide's example as published, not something to copy uncritically into a production
  config without testing at the actual context lengths you intend to use.
- **My own monitoring had a bug, corrected mid-run.** The grep pattern used to count Hermes's tool
  calls (`preparing execute_code|preparing browser|preparing write_file`) silently missed
  `"preparing terminal…"` lines, undercounting actual tool-call volume by roughly 4-5x (true count
  for the Nemotron-3 run was 118, not the ~25 my pattern showed throughout monitoring). This is
  flagged here for transparency — it didn't change the outcome (the run still hit its turn budget
  without finishing, which is the real finding), but it means any "tool call count" cited for
  Hermes runs elsewhere in this benchmark series should be treated as a probable undercount unless
  cross-checked against the session's own final summary line.

## Verdict

You asked for the best answer, not a fair fight, so here it is directly:

**For this kind of agentic, multi-step research task on this DGX Spark, raw `ds4-agent` is
currently the best option** — fastest (25min), zero friction, most specific citations, fully
local, and free of per-token cost. It is not the most capable model in the abstract (DeepSeek V4
Flash q2-imatrix vs a 120B Nemotron), but it is the only one of the three combinations that ran
cleanly end to end with no caveats.

**Hermes adds real, visible overhead without a matching benefit on this hardware.** It's a more
general, more featureful harness (memory, skills, multi-platform gateway — none of which this
task exercised), but on both models tested it was slower than the model's own native tooling
where one existed, and on Nemotron-3 specifically it never reached a usable answer at all. If the
draw to Hermes is its broader feature set for a *different* kind of workload (cross-session
memory, Discord/Slack/Telegram integration, scheduled skills), that's a real and separate reason
to use it — but for "run a research task once and get an answer," it is currently the slower,
less reliable choice on this hardware.

**Nemotron-3-Super is a real, working model on this hardware** — the smoke tests prove that
conclusively — **but the specific serving configuration in NVIDIA's own example guide
(NVFP4 + MTP speculative decoding) degrades badly under the kind of long, accumulating-context
agentic session this task requires.** Before trying Nemotron-3 again for agentic work, the fix to
try first is disabling or re-tuning speculative decoding (drop `--speculative_config` or reduce
`num_speculative_tokens`) rather than assuming the model itself is unsuitable — the smoke tests
show the model and tool-calling integration are both fine in isolation; it's the long-context
decoding throughput under this exact config that broke.
