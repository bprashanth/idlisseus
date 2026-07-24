# Benchmark: model positioning — control plane vs reasoning plane

**Feature (CONCEPT_MAP Block L, ARCHITECTURE §4).** Put a smarter model only where it earns its cost — a
cheap **clarify-gate** in front and a cheap **synthesizer** out back, with the tool-running middle on the
cheap model. The clarify classifier (glm-5.2 scored 0.94) and the assembled "bookends" mode
(`chat.sh --smart-model/--cheap-model`, `eastern_ghats_run/assembled.py`) are **BUILT but not default**.
This bench decides whether to make them default, and in what exact configuration.

**Prior findings to respect (don't re-litigate):** a smart *planner* buys nothing (+33% time, 0 quality);
just-smart-all-around (deepseek-v4) beat very-smart+mid (glm+qwen); qwen-122b's specific weakness is
**asking for clarification**. So the hypothesis is edges-not-planner, and the likeliest win is the
**clarify-gate** specifically.

- **Hypothesis:** a cheap clarify-gate (glm/deepseek classifier) in front of the baseline runner raises the
  ask-when-ambiguous rate and end-to-end answer quality **without** a latency/cost blowup; a smart
  synthesizer out back shortens/cleans the final answer.
- **Baseline:** `docs/REGRESSION_SUITE.md` baseline (single deepseek-v4, discipline plugin only).
- **Arms:** (a) baseline; (b) baseline + clarify-gate; (c) baseline + synthesizer; (d) full bookends.
- **Harness:** `benchmarks/place_memory_run/conv_bench.py` (multi-turn) + `eastern_ghats_run/assembled.py`;
  clarify accuracy from `clarify_classifier.py`.
- **Metrics:** ask-when-ambiguous rate (G1), answer quality (rubric), **latency**, **$/turn**, tool-count.
  Guard: golden suite green.
- **Pass rule:** an arm wins if it beats baseline on ambiguity-handling + quality with ≤ ~1.3× latency and
  no golden regression. Cheapest winning arm ships.
- **Integrate-if-wins:** make the winning arm the chat.sh default (or a documented flag), fold the
  clarify-gate into the `discipline` plugin / control plane as a hook; update `MODEL_OPTIONS.md` +
  `ARCHITECTURE.md §4`. Independent commit.
