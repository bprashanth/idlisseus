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

## L4 (resolver-bypass guard), L2 (where→transfer routing), perf — PENDING.
