# Connector playbook (read this first)

You have **connectors** for live geospatial data. Use them instead of writing
Earth Engine code yourself.

## The pattern for any spatial question

1. **Get points** — a table with `lat`,`lon`:
   - from an asset CSV (the connectors autodetect the lat/lon columns), or
   - `occurrence.search("<species>", aoi)`.
2. **Annotate points** — call the connector that adds the column you need:
   - `landcover.classify(points)` → `+landcover`
   - `fire.exposure(points, radius_km, years)` → `+fire_count`
   - `terrain.at(points)` → `+elevation,+slope`
   - `protected_areas.contains(points)` → `+in_pa,+pa_name`
   - `greenness.trend(points, years)` → `+ndvi_slope,+trend_class` (recovery over time)
3. **Group / rank** with pandas. This part is yours.

## Know the site (EBTL)

If the question is about **"our site" / "the restoration site" / Elephants by the Lake**, read
`/opt/data/connectors/SITE_EBTL.json` for the exact AOI. Use its **`site_bbox_wsen` (~2.9 km)**,
NOT the wide corridor — a good answer is about the 70-acre site, not a 100 km region. At that tight
AOI there is often little/no local data → use the TRANSFER path below (donor points from
`donor_belt_wsen` → `predict.route`).

## When the site has little/no data (TRANSFER — the data-scarcity path)

Many questions are about a **data-poor site** (e.g. Elephants by the Lake, Krishnagiri).
If `occurrence.search` over the AOI returns few/no points, do **not** give up and do **not**
generalise from far-away data blindly. Instead **gather donor points from a wider analog
region and let `predict.route` decide if/how to transfer**:

1. **Get donor points** over a wider, ecologically-similar region (for EBTL: the dry-Deccan
   belt `76.0,11.0,79.5,13.6` — Bandipur/BRT/Mudumalai/Cauvery/Hosur). Exact CLI:
   `python /opt/data/connectors/occurrence.py search --species "<name>" --bbox 76.0,11.0,79.5,13.6 --out /opt/data/work/donor.csv`
2. **Route** — one call decides everything (prints JSON to **stdout** — no `--out`; `--points`
   takes the donor CSV):
   `python /opt/data/connectors/predict.py route --points /opt/data/work/donor.csv --bbox <w,s,e,n> --question presence`
   (use `--question value` for a continuous measurement like canopy/pH). It runs the **gate**
   (is the AOI similar to the donors in satellite appearance AND/OR climate?), runs every
   **valid** method, compares them, and returns a **situation**:
   - `answerable` → report the modelled suggestion **+ its caveat** (say it's modelled, not
     observed; if two methods agreed, say so — it's stronger).
   - `need_more_data` → the honest answer is a **data gap**: tell Varun what to go measure.
   - `need_better_models` → methods disagree; **surface the conflict**, don't average it away.
3. **paper_data is verified ground truth** — check it alongside GBIF; data found in a paper is
   confirmed, and can ground-truth a transfer.
4. **`ebird` for site birds** — for a hotspot (EBTL = `L36453021`), `ebird.py hotspot --loc <id>`
   anchors the site coords and `ebird.py obs --loc <id>` gives per-site bird points (finer than
   GBIF). Needs a free key (warns if unset).

**When data is genuinely scarce (`need_more_data`), SURFACE a concrete nice-to-have dataset** —
don't just refuse. E.g. for invasives/canopy: higher-res hyperspectral (~5 m, e.g. Pixxel) beats
EMIT's 60 m; for birds: acoustic hardware detectors (AudioMoth+BirdNET) and/or structured eBird
effort by habitat. Give the best gated estimate **and** the acquirable next step.

Full reasoning: `predict.md` + `TRANSFER_ALGEBRA.md`. The rule: **be helpful with the data you
have first, then be honest about the limits. Never present a modelled number as observed.**

## Human-use / livelihood questions (firewood, grazing, who-does-what)

These are about **people's behaviour**, which satellites and species-occurrence CANNOT see directly.
**Do NOT force `occurrence`/`predict`/species modelling on them** — that produces irrelevant answers
and loses to a plain chatbot. Instead:
1. Give the observable **PROXY**: forest condition near people — `greenness` trend + `landcover` +
   distance-to-settlement/edge (`geo`, built-up class) → is regeneration weaker near access points /
   villages? That's the satellite-visible footprint of grazing/firewood/extraction.
2. State the honest limit plainly: "satellite can't see who takes what / how many goats."
3. Make the **community-data ask**: household/fuelwood surveys, participatory monitoring, exclosure
   or cut-stump plots, livestock counts. This is the systemic, actionable answer Varun needs.

## Follow the data you HAVE to build a case for more (the abundant-dataset hook)

The most powerful move under scarcity: **anchor the answer in whatever dataset is most abundant
for this site, use it as a bridge to the question via known ecology, then convert the gap into a
concrete data ask.** Never assume which dataset is abundant — CHECK (count what each source
returns: `ebird` species, `occurrence`/GBIF records, `paper_data`). Then:

1. **Bridge the abundant data to the question via ecological relationships.** Example — if BIRDS
   are abundant (e.g. EBTL: 136 eBird species, but ~0 direct plant records) and the question is
   about **plants/invasives/connectivity**: `ebird.py dispersers --loc <hotspot>` lists the
   **frugivores that disperse seeds** (incl. invasive Lantana). That's a mechanistic signal for
   invasive spread + seed rain + which birds move X→Y (corridors) — *even with no plant data*.
   Also: keystone/indicator birds → biodiversity health. (This generalises: use whatever is
   abundant + its known correlates. Do NOT hardcode that birds are always abundant.)
2. **Fill missing fields yourself.** eBird has **no habitat field** — recover "what landscape the
   birds use" by annotating bird points with `landcover.classify`. Similarly annotate with terrain.
3. **State it as a correlation, honestly.** Say plainly: this is a *bridge/hypothesis* from the
   data we have, **not an authority claim** — we're gathering data, not asserting fact.
4. **Ask for the data that would confirm it** — the point is to *instigate action*: e.g. "birds →
   plants → please survey fruiting plants / log habitat on eBird / run plant plots at these
   bird-dense spots," or acoustic hardware, or higher-res hyperspectral (`ebtl/DATA_GAPS.md`).

So for a plant question with abundant birds, Hermes should reason **birds → (diet/dispersal) →
plants → "here's the signal + honest limits + please get us this plant/habitat data."**

## Rules

- **NEVER return an empty or "I couldn't" answer.** If a tool times out or is denied, do NOT keep
  retrying the same heavy call until you run out of turns. Retry ONCE with a smaller/faster call
  (fewer points, smaller bbox, one connector), then **ANSWER ANYWAY** from the data you already
  pulled + established ecology + the honest data ask. A floundering non-answer LOSES to a plain
  chatbot; a short honest grounded answer beats it. Always end a turn with a real answer for Varun.
- **Keep tool calls light so they don't time out.** Sample a modest number of points; prefer one
  targeted connector call over many; if a call is slow, cut its scope rather than repeat it.
- **Never write raw Earth Engine reducer code.** Call the connector.
- **Never guess a class code or band name.** Run the connector's `--describe` to
  get the legend, or read its card.
- Connectors take a CSV of points and return a CSV of points with new columns.

## Invoke (CLI)

```
python /opt/data/connectors/<name>.py --describe
python /opt/data/connectors/<name>.py <function> --points in.csv --out /opt/data/work/out.csv
```

Write `--out` files to a **writable** path like `/opt/data/work/` (`mkdir -p` it
first). The connector and input folders are mounted **read-only**; if `--out`
can't be written the connector prints the CSV to stdout instead (so you still get
the data — capture it).

## Nursery / seed-collection questions

Restoration runs on a nursery, and a nursery runs on seed timing. For "which native to grow /
when do X fruit / seeds to collect now": `phenology.py --species "<sci name>"` gives the empirical
**fruiting & flowering months** (from GBIF observations) → the **seed-collection window**. Then
reason to the **planting window** (Krishnagiri = NE monsoon, ~Oct–Dec): collect seed at fruiting →
propagate → plant at monsoon. Pair with `occurrence` (is the species near the site?), `terrain`/
`landcover` (does the site suit it?), and honestly flag drought-tolerant natives for dry scrub.

For **"which creatures signal a healthy forest / soil / water?"** use `indicators.py --concern
<soil_health|forest_recovery|water_quality|pollination|connectivity> --bbox <aoi>` — it gives the
**sourced** bioindicator taxa (dung beetles, ants, butterflies, spiders, dragonflies…) + what GBIF
actually records near the site. Often the honest answer is "watch + survey these" (a concrete ask);
EBTL already tracks arachnids (→ forest_recovery).

For **water/pond questions** ("which pond dries first?", "how much water do our ponds hold?"):
`water.py ponds --bbox <aoi>` ranks surface-water bodies by how EARLY they dry (JRC seasonality/
occurrence, 30 m) — or `water.py at --points ponds.csv` to annotate known ponds. Pair with
`greenness` (dry-season stress). Sub-30 m farm ponds may be missed → honest gap + field ask.

Available connectors: `landcover`, `fire`, `terrain`, `protected_areas`,
`occurrence`, `greenness`, `ecoregion`, `embedding`, `predict`, `hyperspectral`, `paper_data`,
`ebird` (needs a free key), `phenology`, `indicators`, `water`, `geo`. One card each in this folder.
