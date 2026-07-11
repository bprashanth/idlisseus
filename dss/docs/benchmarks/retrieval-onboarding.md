# Benchmark: retrieval depth + cold-AOI onboarding (combined — the two smaller open questions)

**Feature (CONCEPT_MAP Blocks G + C).** Two medium-size open questions combined into one bench because both
exercise the discovery/loop stack:
- **Retrieval hybrid + the functions-vs-cards question** (Block G, `VISION.md §open`): `discovery` returns
  embeddings top-k only — no LLM re-rank. Prior work said hybrid (emb→LLM re-rank) matched embeddings at
  169 cards; at 256 with distractors a re-rank may now help. And VISION's **functions-vs-cards** question
  (does a richer function/tool over a dataset beat a static card?) was never settled.
- **Cold-AOI onboarding end-to-end** (Block C): only EBTL is battle-tested. Onboarding a genuinely new site
  = `dss/loop/loop.py --aoi <new>` → does scout verify a real data frontier, does the proposer emit sound
  questions, does the agent then answer them?

- **Hypotheses:** (1) an **emb→LLM re-rank** in `discovery.search` beats embeddings-only on the
  `discovery_bench` paraphrased set at 256 cards (higher MRR, no recall loss); (2) a **card is sufficient** —
  a function-over-dataset does not beat cards+extract for the buried-data queries (or, if it does, that's
  the signal to build it); (3) `loop.py` on a **new AOI** (e.g. a second Eastern-Ghats site) produces a
  verified frontier + answerable questions the agent handles at the EBTL quality bar.
- **Baseline:** `discovery` embeddings-only (`discovery_bench/bench.py`, MRR .40 @256) for retrieval;
  EBTL bootstrap output for onboarding.
- **Harness:** `discovery_bench/bench.py` (add a re-rank arm); a new `aois/<second-site>.json`;
  `conv_bench.py` scenarios pointed at the new site.
- **Metrics:** retrieval MRR/recall@5 (re-rank vs emb-only vs +function); onboarding = %verified-frontier
  species with rows, %proposer questions the agent answers non-empty at the new site.
- **Pass rule:** re-rank ships only if MRR up with no recall/latency regression; the function path ships
  only if it clearly beats cards on buried-data queries (else record "cards suffice" and close the VISION
  question); onboarding "passes" when a second site reaches the EBTL golden bar.
- **Integrate-if-wins:** re-rank into `discovery.py` (optional flag → default if it wins); a settled
  functions-vs-cards verdict into `capabilities`/VISION; a second AOI committed as proof of onboarding.
  Independent commits.
