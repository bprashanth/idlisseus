---
name: conservation-data-analysis
description: Analyze ecological restoration sites using geospatial connectors (landcover, greenness, occurrence, predict) and the research-paper corpus. Answer land-cover, recovery, species, taxonomy, and "where" questions with real data — for restoration sites like "Elephants by the Lake" (Eastern Ghats).
tags:
  - ecology
  - conservation
  - remote-sensing
  - land-cover
  - species-distribution
  - herpetofauna
  - arachnology
---

# Conservation Data Analysis

**Trigger**: a question about a site's land cover, forest recovery, species (presence / "where" /
taxonomy / phylogeny / diet), invasives, water, nursery, or ecological condition — especially the
restoration site **Elephants by the Lake** (Eastern Ghats, Krishnagiri).

**Goal**: answer with **real connector + research-paper data**, not general knowledge — and for a
research audience, **beat their own literature review**.

## How to work (thin on purpose — the detail lives in the router + recipes)
1. **Read the router first**: `/opt/data/connectors/PLAYBOOK.md`. It carries the non-negotiables and a
   question-type → recipe table. **Read only the ONE `recipes/<x>.md` that matches** — don't preload all.
2. **The four things that must be true of every answer** (from the router):
   - **Papers first** (`paper_data`) — pull points/values *embedded in datasets*, not just titles.
   - **Resolve the species name** — `points.py resolve --species "<name>"` (a common name can be the wrong
     species); state the scientific name; if `ambiguous`/unmatched, say so.
   - **Honest limit + one concrete data ask** to close.
   - **~3–5 tools then answer; never empty.**
3. **The loop** is always: resolve name → `points.py get` (merged GBIF+iNat+paper, never `occurrence.py
   search` by hand) → annotate (`landcover`/`terrain`/`s2`/`greenness`/…) → group/rank → answer.
4. **Site AOI**: read `/opt/data/connectors/SITE_EBTL.json`; use `site_bbox_wsen` (~2.9 km), not the corridor.

## References (read on demand)
- `references/invasive-mapping-guide.md` — the invasive/"where is X" map workflow.
- `references/ebtl-invasives-profile.md` — EBTL-specific invasive context.
- `references/south-deccan-natives.md` — the dry-Deccan / Eastern-Ghats native species pool.

That's it — everything else is a `recipes/<x>.md` the router points you to. Don't reinvent the workflow here.
