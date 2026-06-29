# Generalized model trial: download → smoke test → Hermes agentic test

A repeatable, parameterized procedure for trying any new open-weight model on this DGX Spark,
modeled directly on how we stood up ds4/DeepSeek V4 Flash and Hermes Agent. Designed to be run
**unguided** by an agent, given one runtime parameter:

```
MODEL = <a model identifier, e.g. an Ollama tag, or a Hugging Face repo id + quant>
```

Do **not** re-run the wildfire-research task as part of this — that experiment is closed. This
plan stops after the Hermes tool-calling smoke test passes (or fails) for the new model. Running
the full agentic research task on a new model, if ever wanted, is a separate, explicit decision
made after reviewing this plan's results — not something this plan triggers automatically.

## Why this is a new procedure (not "just point ds4 at a new GGUF")

`ds4`/DwarfStar is intentionally narrow — it only runs DeepSeek V4 Flash/Pro GGUFs, confirmed from
its own README ("not a generic GGUF runner"). Any other model needs a different serving engine.
Default choice for this plan: **Ollama** — single binary, huge model library, automatic
quantization, trivial `ollama pull <tag>` + built-in OpenAI-compatible API on port 11434. Fall
back to **llama.cpp** (more control, any GGUF, but you build/manage quants yourself) or **vLLM**
(better throughput/batching, heavier setup, best for models too large/slow under llama.cpp-style
backends) only if Ollama doesn't have the model or it needs a specific quant Ollama can't produce.
Record which engine was actually used — it affects the comparison.

## Hard constraints carried over from prior runs (do not re-derive, just apply)

- **Unified memory.** This DGX Spark shares CPU/GPU memory (121GB total). `ds4-server` alone
  holds ~80-90GB when running. **Stop it first** (`sudo systemctl stop ds4`) before loading any
  other model, and restart it (`sudo systemctl start ds4`) once this plan is done with the GPU,
  regardless of pass/fail outcome.
- **Hermes requires ≥64,000 tokens of context** or it refuses to start. Check this explicitly
  (Phase 2) before assuming a model will work with Hermes — don't find out at smoke-test time.
- **Hermes tool-calling depends on the server emitting OpenAI-format `tool_calls`.** ds4 does this
  natively. Generic servers (vLLM, llama.cpp) usually need explicit flags
  (`--enable-auto-tool-choice --tool-call-parser <name>`) matching the model's tool-call format
  (e.g. `hermes`, `llama3_json`, `deepseek_v3` for vLLM). Ollama generally handles this itself for
  models in its library that declare tool support — verify, don't assume.
- **Hermes's data dir (`~/.hermes`) is owned by container UID 10000**, not your shell user. Use
  `sudo` to read/edit `~/.hermes/config.yaml` directly; `cp`/`find` with shell globs against paths
  under `~/.hermes` need `sudo bash -c '...'` so the glob expands under sudo, not your own shell.
- **Pin every `auxiliary.*` sub-task's `provider`/`base_url` in `config.yaml` explicitly to the
  new model**, not just the top-level `model:` block — otherwise some background tasks
  (web_extract, compression, vision, etc.) are left on `provider: auto` and the run is no longer
  unambiguously "this model end to end." (No cloud API keys are configured on this box, so `auto`
  can't actually reach a different paid backend — but pin it anyway for clarity in the record.)

## Phase 0: Capacity check

```bash
df -h /                 # need the model's on-disk size + ~20% headroom free
free -h                 # confirm ds4-server is the only big consumer; stop it (see below)
sudo systemctl stop ds4
free -h                 # confirm headroom freed (~115GB+ available)
```

Stop and report if the model's required disk or memory footprint doesn't fit after stopping ds4.
Don't silently pick a smaller quant without saying so.

## Phase 1: Install the serving engine (if not already present) and pull $MODEL

**Ollama path (default):**
```bash
curl -fsSL https://ollama.com/install.sh | sh    # if not already installed
ollama pull "$MODEL"
OLLAMA_HOST=0.0.0.0:11434 ollama serve &          # or systemd-enable it, matching ds4's pattern
```

**llama.cpp / vLLM path (fallback, only if Ollama can't serve $MODEL):** document the exact build
and serve commands used, the quant chosen and why, and the bind address — follow the same
Docker-bridge-IP-not-`0.0.0.0` pattern used for `ds4-server` if anything else on this box (like
Odysseus) needs to reach it, to avoid exposing a raw, unauthenticated model API on the
LAN/Tailscale interface.

## Phase 2: Smoke test the new model's OpenAI-compatible endpoint directly

Before touching Hermes, confirm the bare server works — same checks as the original ds4 setup:

```bash
curl -s http://<host>:<port>/v1/models                 # confirm it's up, note context_length
curl -s http://<host>:<port>/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"<id>","messages":[{"role":"user","content":"hi"}],"stream":false}'
curl -s http://<host>:<port>/v1/chat/completions ... -d '{... "stream": true}'   # streaming too
```

**GO/NO-GO:** if `context_length` reported is under 64,000, or the server doesn't speak
`/v1/chat/completions` at all, stop here and report — don't try to force Hermes onto a model that
fails this floor.

## Phase 3: Point Hermes at the new model

```bash
sudo python3 - <<'PYEOF'
path = "/home/beeps/.hermes/config.yaml"
# Same technique used for ds4: replace the model: block's provider/base_url,
# then walk the auxiliary: block and pin every provider:auto -> custom + base_url.
PYEOF
```

Set `model.provider: custom` (or the Ollama-specific provider alias if using Ollama's own
provider profile — check `/opt/hermes/plugins/model-providers/` inside the image for the exact
profile name and aliases, same way we found `custom`'s aliases included `ollama`/`vllm`/etc.),
`model.default: <id>`, `model.base_url: http://<host-reachable-address>:<port>/v1`.

## Phase 4: Hermes connectivity + tool-calling smoke test — GO/NO-GO gate

Identical two-step test used for ds4:

```bash
docker run --rm -v ~/.hermes:/opt/data nousresearch/hermes-agent chat -q "What is 2+2? Reply with just the number."
docker run --rm -v ~/.hermes:/opt/data nousresearch/hermes-agent chat -q "List the files in your current working directory."
```

**If either fails** (wrong answer, tool-calling format mismatch, hang, crash): **stop, do not work
around it, report the exact failure.** This mirrors the explicit instruction from the ds4 trial —
a silently-patched failure here would make any later agentic comparison meaningless.

**If both pass:** record token throughput if observable, note tool-call count/timing for the
second test (ds4's baseline was instant single-digit tool calls; Hermes+ds4 in the full wildfire
run showed real friction — ~30% of tool calls hit a 60s timeout-denial before succeeding — note
whether the new model+engine combination shows similar or different friction).

## Phase 5: Stop and report

This plan ends here. Do not proceed to any agentic research task automatically. Restart ds4:

```bash
sudo systemctl start ds4
curl -s http://172.17.0.1:8000/v1/chat/completions ...   # confirm it's back before declaring done
```

Write results to `benchmark2_hermes/models/<model-name>/`:
- which engine was used and why
- exact pull/serve commands
- Phase 2 and Phase 4 transcripts/output
- pass/fail verdict and, if failed, the exact failure point and error text
- disk/memory footprint actually observed
