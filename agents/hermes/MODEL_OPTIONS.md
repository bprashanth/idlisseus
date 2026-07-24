# Model options for `chat.sh` (which model to run the agent on)

How the agent behaves depends on the model, mostly around **tool-call parallelism** and **discipline**.
The `discipline` plugin (`plugins/discipline/`) adapts per-model automatically; this file records the
tradeoffs + the open fix.

## The models
| via `chat.sh` | what it is | cost | parallelism (batched tool calls) | notes |
|---|---|---|---|---|
| `-m qwen122b` (default) | local Qwen3.5-122B INT4+FP8 on vLLM (172.17.0.1:8001) | free | **NO — serial only** | capable but see the parser bug below |
| `-m deepseekv4` | DeepSeek-V4-Flash via OpenRouter | cheap | **YES — batches cleanly** | tested: multi-turn, 0 empty-name, 0 errors |
| `-m glm5.2` | GLM-5.2 via OpenRouter | pricier (reasoning) | YES | strong reasoning; best clarify classifier (0.94) |
| `ds4` (systemd, GPU switch) | local ds4 C+CUDA | free | untested | different serving stack; would need a model switch |

## The parallelism finding (why qwen is serial)
Isolated test (same batch-tempting query): **qwen → 2 phantom empty-name calls; deepseek → 0.** Root cause
is the vLLM **`--tool-call-parser qwen3_xml`**: when qwen emits several tool calls in one message, the parser
wedges a phantom `name='' args='{}'` call between the valid ones → hermes tries to run it → `Unknown tool ''`
→ agent-correction retries → "stopping as partial". Single calls are fine. It is a **parser artifact, not
the model's intelligence** — a dumber qwen (same parser) would fail identically.

**NOT the cause:** the token proxy (`token_proxy.py`) is **inactive**, and even running it only corrects
`max_tokens` for `qwen3-next-80b` (a passthrough for our `"qwen"`). Ruled out.

**Handled today:** the `discipline` plugin reads the `model` in `pre_llm_call` and injects
*serial* for qwen, *batch* for deepseek/glm. SOUL.md is neutral on tool-count (a model-specific parser
workaround does NOT belong in the always-on persona). So qwen stays safe; deepseek/glm get concurrency.

## Open fix to let qwen batch too (unattended-restart risk — do with care)
Swap the vLLM parser: restart `vllm-qwen35` with `--tool-call-parser hermes` (or bump vLLM to a version
with the `qwen3_xml` multi-call fix). If it parses batches cleanly, drop the qwen→serial special-case.
Grab the current launch command from `models/qwen3.5-122b/` first so it's a clean, revertible change.
(Alternative isolation test: run **ds4** — different stack — to see if it batches clean.)

## Recommendation
- **Want parallelism + a capable model:** `-m deepseekv4` (cheap, batches clean, handles multi-turn well).
- **Want free/local:** default qwen (serial, safe, still short+honest via the plugin).
- **Don't stack smart models.** Adding a glm clarify-gate/synth *on top of* deepseek is the
  "planner-buys-nothing" anti-pattern — deepseek already clarifies/proceeds and drills multi-turn on its
  own. Reserve glm for: (a) the deterministic **clarify classifier** if you want to make qwen's variable
  clarify reliable (`benchmarks/place_memory_run/clarify_classifier.py`, 0.94), or (b) running the agent
  *as* glm when you want its reasoning.

## Last deepseek trace (2026-07-11, 4 turns) — assessment
"tell me about invasives" → "check papers first" → "invasives↔snakes relationship" → "design the survey".
**Parallelism: batched (4 calls/msg), 0 empty-name, 0 errors — clean.** Multi-turn drilled well; honest
("zero snake records, backed by 0"); ended with a concrete stratified survey design. One nit: answers
**creep long** on deepseek (final was 1714 ch vs the ~1100 target) — if that bugs you, tighten the plugin's
terse nudge or lower `_CAP` for the deepseek path.
