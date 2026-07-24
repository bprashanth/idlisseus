# Next steps — where this can go

Three tiers, cheapest first. We've done tier 0. Tiers 1–2 are optional and heavier.

## Tier 0 — what we have (the "system improves, weights don't" loop)
The library of tested connectors + the KB + the playbook rules get better over time,
but the **local 122B model's weights never change**. When the agent hits something it
can't do (write a correct spatial reduction, a new connector), a **frontier writer**
(cursor / a human) fills the gap, gated by a self-test. This already works and is the
right first phase — cheap, safe, auditable.

## Tier 1 — richer retrieval + full-text data (small, do next if useful)
- **Better `ask.py` retrieval.** Today it's keyword-overlap (simple, transparent, but
  loose). Swap in a small embedding model (`bge-small`/`sentence-transformers`) over
  `kb.jsonl` for semantic search. ~half a day.
- **Full-text CSV/table extraction** — Unpaywall → pull the *data tables* out of the
  1,783 papers we already found (beyond abstracts). Turns papers into usable numbers.
- **Dataset-card broker** — the original `PLAN.md` experiment we never ran (auto-generate
  a card per dataset, embed, compare cursor-vs-122B card quality, Recall@5).

## Tier 2 — make the LOCAL model itself better (the "second, heavier loop")
Right now the *system* gets smarter while the *weights* stay fixed. The next level is
teaching the local 122B to do the hard parts **itself** — write correct connectors and
spatial code from scratch — so it needs less frontier hand-holding.

**We already sit on the training data + the reward signal:**
- **Trajectories:** Hermes' `~/.hermes/state.db` stores the *exact Python code* per
  `execute_code` call — every attempt, successful or not.
- **Labels/reward:** the **self-test gate** and the **judge** already say which
  connector/answer was *correct* (gold-matched). That is a ready-made reward function —
  the expensive part of any RL setup, and we built it for free as a side effect.
- **Ledger:** `question → plan → gold → lineage` records are supervised examples.

**Tooling (Nous / TM ecosystem — worth knowing it exists):**
- **GEPA** (reflective **prompt** evolution) — *start here.* Evolve the PLAYBOOK /
  system prompts from the traces. No weight training, cheap, often most of the win.
- **SFT** — fine-tune on the *successful* traces (the code that passed the self-test).
  Straightforward supervised step once enough gold traces exist.
- **Atropos** (Nous RL-environment framework for agent trajectories) + **Tinker**
  (managed fine-tuning/RL API) — full RL, using the self-test/judge as the reward, to
  push the model past what SFT imitation gives.

**Sequence:** GEPA (prompts) → SFT (imitate gold traces) → RL (Atropos/Tinker, reward =
self-test/judge). Each is a bigger lift than the last.

**When:** *not now.* It needs a larger corpus of gate-validated traces than one run
produces — collect those first (keep the loop's `state.db` + ledger). The key asset is
already in place: **a machine-checkable reward (the self-test gate).** Most agent-RL
projects have to build that; we have it.

**Honest caveat:** fine-tuning a 122B locally is a real infra lift (GPU-hours, eval
harness, regression risk). GEPA + SFT capture much of the value for far less; only reach
for RL if a specific, measurable weakness justifies it.
