# Benchmark 2: Hermes Agent (+ds4) vs raw ds4-agent — agentic research workflow

## Goal

Cursor is dropped from this round. Compare two ways of using the same local model (ds4 /
DeepSeek V4 Flash) on a genuinely agentic, open-ended task:

1. **Hermes Agent** (NousResearch) running in CLI mode, configured to call ds4 as its model
   provider.
2. **Raw `ds4-agent`** (ds4's own built-in terminal coding/tool-use agent), used directly,
   no Hermes in the loop.

Both get the *same* underlying model and hardware. The variable under test is the agent
framework/harness around the model: memory, skill system, tool design, planning — not model
quality (that was Benchmark 1's question).

## Task: Ecological Research Assistant

**Revised scope (per user, after Phase 1 passed):** the agent itself must find and download the
corpus — we do not pre-source it. Both systems get the same prompt:

> Research wildfire risk interventions for the Nilgiris and Himalayan region. Find and download
> roughly 10 relevant papers and a few reports (a few reliable starting points: Zenodo, and NGO
> publications on wildfire/forest-fire management in this region — but don't limit yourself to
> those). Save everything you download to a stable local directory. Then answer: what
> interventions are supported by evidence? What disagreements exist in the literature? What would
> you recommend measuring? Support your claims with a dashboard. Include citations.

No specific document list, no exact URLs — the agent has to search, decide what's relevant,
download it, and keep it somewhere persistent so we can audit exactly what it found afterward.
This tests real tool-use (web search/browse, download, file organization) in addition to
synthesis and citation quality.

## Hard stop condition

Phase 1 (below) is a go/no-go gate. If Hermes cannot be made to talk to ds4 at all — config
incompatibility, tool-calling format mismatch, context-window rejection, or anything else — stop
and report back rather than working around it silently. This is explicitly the user's instruction.

---

## Phase 0: Identify Hermes precisely

Done — confirmed via NousResearch docs/GitHub (`nousresearch/hermes-agent`):

- Connects to any server implementing `/v1/chat/completions` (OpenAI-compatible).
- CLI mode: `docker run -it --rm -v ~/.hermes:/opt/data nousresearch/hermes-agent` (no `gateway`
  subcommand — that's the multi-platform messaging daemon mode, explicitly out of scope here).
- Hard requirement: model must expose **at least 64,000 tokens** of context, or Hermes refuses to
  start. ds4-server here runs with `--ctx 100000`, so this should not be a blocker.
- Custom provider config lives in `~/.hermes/config.yaml`:
  ```yaml
  model:
    default: deepseek-v4-flash
    provider: custom
    base_url: http://<ds4-reachable-address>:8000/v1
    api_key: "none"
  ```
- ds4-server's own docs confirm it natively maps its DSML tool-call format to OpenAI
  `tool_calls` on `/v1/chat/completions` — no vLLM-style `--tool-call-parser` flag needed on the
  server side, unlike the generic guidance in Hermes's docs (that guidance targets vLLM/llama.cpp
  servers, not ds4's native implementation).

## Phase 1: Install Hermes (Docker, CLI mode) and verify it talks to ds4 — GO/NO-GO

1. `docker pull nousresearch/hermes-agent`
2. Run `... hermes-agent setup` once to initialize `~/.hermes`.
3. Write `~/.hermes/config.yaml` pointing `base_url` at ds4 (same Docker-bridge-IP pattern used
   for Odysseus in the main POC, since ds4 is bound to the bridge IP, not `0.0.0.0`).
4. Run Hermes interactively (`docker run -it --rm ...`, no `gateway` arg) and send one trivial
   prompt ("what is 2+2", "list files in this directory").
5. **If this fails:** stop, report the exact failure, and brainstorm with the user rather than
   forcing it.
6. **If this succeeds:** proceed to Phase 2.

## Phase 2: Verify each agent can actually search + download (capability check)

Before the full run, confirm each agent has working internet access and a download path (curl,
browser tool, or both) from inside its sandbox — Docker containers and ds4-agent's own bash tool
both need outbound network access for this task to be possible at all.

## Phase 3: Run Hermes+ds4 on the task

Hermes does not load its own model copy (it calls ds4-server over HTTP), so this can run while
`ds4-server` stays up. Single CLI invocation with the research prompt above, workspace pointed at
a stable directory (`~/.hermes/workspace/wildfire_research/`). Capture full transcript, timing,
the downloaded corpus, and all output artifacts (dashboard, citation list).

## Phase 4: Run raw ds4-agent on the same task

ds4-agent loads its own model copy, so `ds4-server` must be stopped first (unified-memory
constraint from Benchmark 1) and restarted afterward. Same prompt, workspace
`benchmark2_hermes/ds4_agent_run/`.

## Phase 5: Compare

- Did each correctly ground claims in the provided corpus (citation accuracy — do the citations
  point to real, correct documents/sections, not hallucinated ones)?
- Did each surface real disagreements in the literature, or just summarize uncontroversially?
- Quality/usefulness of the measurement recommendations.
- Quality and correctness of the dashboard.
- Time, tool-use trace quality (how each one searched/read/cross-referenced the corpus), and any
  use of Hermes's memory/skill system that raw ds4-agent has no equivalent for.

## Phase 6: Write report (interim, ds4-only)

`benchmark2_hermes/REPORT.md` covering Phase 3 (Hermes+ds4, done) and Phase 4 (raw ds4-agent),
same evidence-based style as Benchmark 1's report. This is interim — final report folds in
Nemotron-3 once Phases 7-10 below are done.

---

## Phase 7: Download and set up Nemotron-3-Super

Per NVIDIA's own DGX Spark deployment guide:
https://github.com/NVIDIA-NeMo/nemotron/tree/main/usage-cookbook/Nemotron-3-Super/SparkDeploymentGuide

Model: `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4` (120B params, NVFP4 4-bit, ~80.4GB on
disk across 16 safetensor shards — confirmed via the HF API before download, not gated, no
HF_TOKEN strictly required). Architecture: hybrid Mamba-2 SSM + attention ("LatentMoE"), with
built-in MTP speculative decoding.

Serving engine: **vLLM** (`vllm/vllm-openai:cu130-nightly` Docker image), not ds4 — ds4 only runs
DeepSeek V4 GGUFs. This is also the first real test of whether vLLM's continuous batching closes
the "no concurrent requests" gap we found with ds4 in Benchmark 1.

**Use the NVIDIA guide's config as-is, including `--max-model-len 1000000`.** The guide is written
for exactly this hardware (single DGX Spark, 128GB unified memory) and `ds4-server` will be
stopped before this runs, so Nemotron-3 gets the whole machine, same as ds4 got the whole machine
during its own tests — there's no sharing constraint during the run itself, so no reason to
under-configure it. The goal here is best real performance on this box, not a context-budget-
matched "fair fight" against ds4. Still record actual observed memory use once it's up (don't
assume it fits just because the guide says so for "a DGX Spark" in the abstract) — if it doesn't
fit at 1M context on actual measurement, reduce only as far as necessary and say so, rather than
pre-emptively shrinking it.

**Known risks to check, not assume past:**
- `vllm/vllm-openai:cu130-nightly` must actually publish an arm64 manifest — DGX Spark's Grace CPU
  is aarch64, and many vLLM nightly images are amd64-only. Check before any long download.
- `--gpus all` Docker GPU passthrough is already confirmed working on this box (main POC), but
  NVFP4 + Blackwell-specific kernels are new territory — first run may fail for backend reasons
  unrelated to setup correctness.
- Stop `ds4-server` first (unified memory).

## Phase 8: Smoke test Nemotron-3 directly (same two-step check as ds4)

```bash
curl -s http://<host>:8000/v1/models                          # confirm context_length, etc.
curl -s http://<host>:8000/v1/chat/completions -d '{...stream:false}'
curl -s http://<host>:8000/v1/chat/completions -d '{...stream:true}'
```
GO/NO-GO: stop and report if the server won't start, won't load the model, or context_length
reported is under Hermes's 64k floor.

## Phase 9: Point Hermes at Nemotron-3, repeat the tool-calling smoke test (GO/NO-GO)

Same procedure as `PLAN_MODEL.md` Phases 3-4: edit `~/.hermes/config.yaml`, pin
`model.provider`/`base_url` AND every `auxiliary.*` sub-task to Nemotron-3's endpoint (not left on
`auto`), then run the trivial-prompt test and the tool-calling test. Use vLLM's documented
`--tool-call-parser qwen3_coder` server-side flag (per the NVIDIA guide) — this is a real
difference from ds4, which needs no such flag because it maps tool calls internally; if Hermes's
tool calls don't come through correctly with this parser, that is itself a reportable finding,
not something to route around silently.

## Phase 10: Run the wildfire research task on Hermes+Nemotron-3

Identical prompt used for Hermes+ds4 in Phase 3. Same workspace pattern
(`~/.hermes/workspace/wildfire_research/` or wherever it actually lands — audit, don't assume).

## Phase 11: Final comparison report

**Per user clarification: no raw-Nemotron condition** — Nemotron-3 ships no equivalent to
`ds4-agent` (no built-in multi-step tool-use harness of its own), so there's nothing meaningful
to run "raw." Three-way comparison only:

| Condition | What it tests |
|---|---|
| ds4 (raw `ds4-agent`) | Model + its own shipped multi-step tool-use harness |
| Hermes + ds4 | Same model, Hermes harness instead |
| Hermes + Nemotron-3 | Different model, same Hermes harness |

`benchmark2_hermes/REPORT.md`, folding in Benchmark 1's findings (ds4 vs Cursor) for context.
Cover: citation accuracy/honesty, evidence-ranking quality, dashboard quality, wall-clock time,
tool-call efficiency/friction (timeouts, retries), and throughput/memory characteristics — this is
also the first chance to check whether vLLM's continuous batching changes anything from
Benchmark 1's "ds4 doesn't batch concurrent requests" finding. The point of this whole exercise is
to find what's actually best to run on this hardware, not to force a context-budget-matched fair
fight — say plainly if one combination is just better.

---

## Operating instruction: checkpoint frequently

This plan is meant to run unattended over a long session. **After every phase boundary** (pass or
fail), append a dated entry to `benchmark2_hermes/CHECKPOINT.md` recording: which phase just
finished, pass/fail and why, key facts needed to resume (PIDs, ports, file paths, config state,
whether ds4-server is currently up or down), and the next planned action. This is so that if
context gets compacted mid-run, picking the plan back up means reading `CHECKPOINT.md` first, not
re-deriving state from scratch.
