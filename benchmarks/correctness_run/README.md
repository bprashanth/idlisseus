# correctness_run — the L1/L2/L4 correctness cluster (bench spec: dss/docs/benchmarks/correctness-routing.md)

## L1 — name resolution (confident wrong-species). DONE 2026-07-12.

**Bench:** `name_cases.tsv` = 12 EBTL-relevant common names → expected genus/species (incl. traps).
Measure `points.py resolve` (deterministic, no agent) — the metric that matters is **confident
wrong-KINGDOM** answers (asserting a plant/insect for an animal), the real L1 harm.

**Baseline finding:** `resolve` returned **2 confident wrong-kingdom answers** — `gaur` → *Chamaenerion*
(fireweed, a PLANT) and `sambar` → *Crocothemis* (a DRAGONFLY). Root cause: for a bare common word, iNat
autocomplete returns typo-fuzzy garbage from the wrong kingdom, and the fuzzy branch picked the
**most-observed** hit and asserted it. (iNat had zero real match for "gaur"; for "sambar" the correct genus
*Rusa* was present but lost the (SPECIES-rank, obs) ranking to a common dragonfly.)

**Fix** (`points.py resolve`, fuzzy branch): a **whole-word relevance guard** — only trust a fuzzy hit whose
common/scientific name shares a WORD with the query; otherwise resolve to NOTHING (`scientific=None` +
"UNVERIFIED; ask which species"). An honest unresolved beats a confident wrong-species. Whole-word (not
substring) so "gaur" no longer matches the plant "Gaur**a**".

**Result:** confident wrong-kingdom **2 → 0** (gaur, sambar now honest-unresolved). All 7 clear animals
still resolve correctly (green cat snake → *Boiga cyanea*, cobras, vipers, elephant, sloth bear). The other
label "misses" are iNat quirks, not errors: *Lantana strigocamara* is the accepted name; *Rhinophis* is a
valid shieldtail; "spotted deer" is a shared common name (chital/sika) handled by the ambiguity flag.
Gate: golden suite re-run on deepseekv4 (green_cat_snake still resolves + flags).

**Follow-up (optional):** gaur/sambar are real EBTL fauna — a small curated site-vernacular alias map
(gaur→*Bos gaurus*, sambar→*Rusa unicolor*, spotted deer→*Axis axis*) would resolve them correctly and
disambiguate toward the India-native. Kept out of this commit to avoid overfitting the general fix.

## L4 — resolver-bypass guard. DONE 2026-07-12.

**Finding:** recent traces had **15 direct `occurrence`/`inaturalist`-by-name calls** vs 85 via
`points.get` (~15% bypass the resolver → a common name can map to the wrong species).

**Fix** (`agents/hermes/plugins/discipline/__init__.py`, `pre_tool_call`): a guard that **blocks** a tool
command containing `occurrence.py`/`inaturalist.py` **with `--species`** (a NAME) and redirects to
`points.py get`. Allows `--describe`, already-resolved `--taxon-key`, and never touches `points.py get`
(which resolves internally). Doesn't count against the tool cap. Unit-tested (6/6: blocks by-name,
allows resolver/describe/taxon-key/other connectors).

**Smoke (deepseekv4, "how many king cobra records around EBTL"):** answered correctly (15 records, all
Western Ghats, none at EBTL, OBSERVED + 15 GBIF pts, predict refused to model, 3 follow-ups) using
`points.get` ×5, 0 direct-by-name — guard is a validated safety net that doesn't harm the normal flow.
Gate: golden --run green (new vs `results_base_ref.jsonl`).

## L2 — where→transfer routing. VERIFIED HANDLED (no code change) 2026-07-12.

L2 (a "where can I find X" question returning a raw point instead of routing to the transfer/map pipeline)
was a **local-qwen** behavior. On the deepseek baseline + the `recipes/spatial-where.md` recipe it routes
correctly: probe "where can I find russell's viper across our site?" → resolved 356 regional donor records,
ran `predict` (transfer pipeline), labeled modelled/likelihood, offered the rendered suitability map as a
follow-up (not a single GPS dot). The golden `green_cat_snake` ("where") also passes with transfer-flagging.
So L2 is satisfied on the baseline — recorded here rather than "fixed" (no coercion; don't invent a change
that isn't needed).

## Transfer perf (RF retrains every call → covariate cache) — DEFERRED.
Real but a larger optimization (cache sampled AlphaEarth/WorldClim vectors per donor+AOI point, add a
sklearn local fast-path). Latency is currently acceptable (~1–1.5 min for a modelled "where"). Own session;
bench spec `dss/docs/benchmarks/correctness-routing.md`.
