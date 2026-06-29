# Benchmark 3: Seed-OSS-36B-Instruct vs ds4 (DeepSeek V4 Flash) — literature/document synthesis

## Why this benchmark is different from Benchmark 2

Benchmark 2 tested agentic search+download+synthesis end to end, with the harness (Hermes vs
native agent) as the variable under test. This round isolates **synthesis quality on a fixed,
known document set** — no search, no download, no agent harness. Direct API calls to each model
only. Motivation: Seed-OSS-36B is a dense model explicitly tuned for agentic/coding benchmarks,
not obviously better at literature synthesis than a much larger MoE — worth testing directly
rather than assuming either way. Also motivated by interactive-use latency ("quicker tasks and
answers via Odysseus").

## Hardware reality check (done before starting)

- Disk: 626GB free, no issue (72.3GB BF16 weights).
- Memory: **cannot run alongside ds4.** ds4-server alone uses ~108GB of 121GB unified memory,
  leaving ~13GB free — not enough for Seed-OSS-36B at any practical quant (even 3-4 bit GPTQ/AWQ
  needs ~16-20GB). ds4-server is stopped for the duration of this benchmark and restarted after.
- Using native BF16 (NVIDIA's own recommended precision), not a smaller quant — Seed-OSS gets the
  whole machine to itself during this benchmark, same principle applied to Nemotron-3: best
  available performance, not pre-emptively shrunk for a sharing constraint that doesn't apply
  during the test itself.

## Aside, confirmed while planning this: ds4's "Pro" option is not a second model

Checked `/v1/models` and ran identical prompts against `deepseek-v4-flash` and `deepseek-v4-pro`
— both IDs serve the exact same loaded q2-imatrix Flash GGUF (ds4's own `--help` text says so
explicitly: "Model endpoint aliases include deepseek-v4-flash and deepseek-v4-pro; both serve the
loaded GGUF"). The model gives different (both wrong) self-reported parameter counts depending on
which alias it's called under, suggesting an alias-dependent system hint, but compute cost and
real capability are identical. Odysseus showing "both work" is true but not meaningful — there is
only one model resident.

## Document set

5 papers picked from Benchmark 2's real downloaded wildfire/forest-fire corpus (not re-downloaded
— reusing known, already-vetted real documents), copied + text-extracted via `pdftotext` into
`papers/`:

- `01_Models_Forest_Fire_Management_India` — general models/management, frames causes as
  predominantly anthropogenic
- `03_Forest_Fire_Himalayan_Regions` — Himalayan-region focus
- `09_Wildfire_Burn_Severity_Uttarakhand` — burn-severity remote-sensing science
- `11_Cloud_Based_Fire_Alert_IoT` — IoT/tech detection angle
- `16_Madhuca_Longifolia_Fire_Cause` — attributes a meaningful share of fires to Mahua-flower
  collection specifically, a deliberate contrast with (01)'s general-anthropogenic framing, to
  give the disagreement-synthesis task something real to find

Combined: 11,765 words (~15-16K tokens), comfortably inside both models' context windows.

## Task battery (identical prompts to both models, direct `/v1/chat/completions` calls)

1. **Single-document summary** — summarize one paper (Himalayan regions paper) in ~3 paragraphs.
2. **Multi-document synthesis** — given all 5 papers' text, identify agreements and disagreements
   across them.
3. **Targeted grounded Q&A** — a question answerable only by cross-referencing two specific
   papers (cause-attribution paper vs. the general-management paper), checking for honest
   "not stated" vs. fabrication on anything not actually in the text.
4. **One-shot dashboard** — given all 5 papers, ask for a complete, self-contained
   `dashboard.html` as the response text (no tool use — this is a one-shot generation test, the
   same deliverable type Benchmark 2's agents produced via tool calls, here produced directly by
   the model in one response). I save whatever it outputs verbatim to a file.
5. **Short-prompt latency/throughput** — simple, short prompts unrelated to the documents,
   measuring time-to-first-token and tokens/sec, since responsiveness for quick interactive use
   (the Odysseus use case) is a separate axis from synthesis quality.

## Setup

vLLM (`vllm/vllm-openai:cu130-nightly`, already cached from Benchmark 2), adapted from NVIDIA's
8-GPU example to single-GPU:

```
vllm serve ByteDance-Seed/Seed-OSS-36B-Instruct \
  --tensor-parallel-size 1 \
  --enable-auto-tool-choice \
  --tool-call-parser seed_oss \
  --max-model-len 65536
```

Bound to `172.17.0.1:8000` (docker bridge IP), same security pattern as every other model trial
this session — reachable from other containers, not from LAN/Tailscale.
