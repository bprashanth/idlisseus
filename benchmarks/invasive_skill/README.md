# invasive_skill — benchmark for improving the free invasive-detection skill

## What this is (read first)

There is a **working, free invasive-detection skill** already deployed in the Hermes agent + the DSS. When
a field worker asks the agent a question that evaluates data over an area — *"is lantana taking over?",
"where is the lantana on our land?", "what's spreading here?"* — Hermes invokes this skill: it pulls the
species' records, models an **invasive-likelihood map** from free satellite data, and returns a
field-navigable map + GPS waypoints, honestly labelled *likelihood, not a confirmed ID*. It works today.

**This benchmark is NOT for building that skill — it already exists.** It is a **separate playground to
improve the modelling** behind it: better change-detection, a trained classifier, spectral methods, active
learning, high-res fusion. Another agent can pick this up in isolation, run experiments, and swap in a
better algorithm **without touching the main master plan.** The skill's public interface (its inputs and
its `data.json`/map outputs) is the contract; you improve what's *inside*.

## The big picture (so you're not lost about goals)

The overall project (`benchmarks/algebra/MASTER_PLAN.md`, converging into `dss/`) builds a replicable
conservation Decision-Support System that beats a context-free frontier CLI on a real site — **EBTL**
("Elephants by the Lake", a ~70-acre dry-deciduous restoration near Krishnagiri, Tamil Nadu; site centre
12.734 N, 78.183 E). Core constraint everywhere: **data scarcity**. Skills are categorised by an algebra
(`../semantic_broker/SKILL_ALGEBRA.md`): STATE / RELATION / CHANGE / TREND / VALUE, with TRANSFER and
GROUND-TRUTH as cross-cutting layers. **The invasive map = CHANGE + TRANSFER**, verified with the
GROUND-TRUTH lens. Keep new work inside that vocabulary.

## The working skill (what exists, where)

All in `../semantic_broker/connectors/` unless noted:
- **`invasive.py`** — the deployed skill. `invasive.py map --species "<name>"` → trains an Earth-Engine
  RandomForest on the species' recent GBIF records (auto-widens if sparse; phenology-only fallback) over a
  6-band Sentinel-2 stack + multi-year stay-green phenology → `data.json` + field-navigable HTML + GPS
  waypoints. Runs in the Hermes container. Wired into `PLAYBOOK.md` ("where are the invasives").
- **`s2.py`** — Sentinel-2 primitives incl. `anomaly*` (the stay-green phenology signal).
- **Ground-truthing (the eyescan):**
  - `../experiments/label_sheet.py` → a clickable sheet of 35 cm crops the user tags Lantana/not → CSV of labels.
  - `groundtruth_lens.py` → the reusable lens map (multi-method prediction + cursor lens onto high-res).
  - `../experiments/a2_segment.py` → the high-res (Vantor) appearance detector + concordance with the free map.
- **`skyfi.py`** — buy/download high-res archive imagery (budget-guarded). See `../experiments/RESUME_VANTOR.md`.

## What we already learned (don't repeat these)

- The free CHANGE map (phenology + transferred RF) is **weak but real** — max likelihood ~0.59 at EBTL,
  driven mostly by phenology (the transferred RF is soft because the nearest Lantana records are 20–40 km away).
- **Hand-crafted appearance rules FAIL** on the 35 cm scene (they flag orchards + dry soil as Lantana).
  Verified visually. → a *trained* classifier on real labels is the way, not more hand rules.
- Free map (A1) and high-res appearance (A2) **disagree** at their hotspots (concordance rho ~0.36) — both
  are uncalibrated. **The missing ingredient is ground-truth labels.** (Full write-up:
  `../semantic_broker/experiments/INVASIVE_MAP_BENCHMARK.md`.)

## Your job here

Improve the map via better modelling — see **`IMPROVE_ROADMAP.md`** for the ranked experiment menu (a
phenology *time-series* classifier is the highest-value free upgrade), **`DATA_AND_KEYS.md`** for every data
source + API key + how to get more, and `../semantic_broker/SKILL_ALGEBRA.md` for how to categorise any new
skill/tool that falls out. When an experiment beats the current skill on the agreed metric (H1/H2/H3 in the
benchmark doc), fold it back into `invasive.py` behind its existing interface.
