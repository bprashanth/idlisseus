# Connector playbook (read this first)

You have **connectors** for live geospatial data. Use them instead of writing
Earth Engine code yourself.

## ✅ NON-NEGOTIABLE final-answer checklist (the benchmark keeps catching these)

Before you send ANY answer, check all three — models most often miss these:
1. **Named a species? Verify or label it.** If you name a specific species (esp. "what grows near X" /
   nursery / diet questions), either run one `occurrence.search "<species>" <aoi>` to confirm it's recorded
   locally, OR say plainly "typical for this ecoregion, not verified at your site". Never assert a species
   list from memory as fact.
2. **End with the honest limit + ONE concrete data ask.** Every answer closes with what the data does NOT
   show (label proxies/modelled/coarse) and the single most useful thing to collect next. A confident
   answer with no caveat loses the benchmark.
3. **"Where is X / where are the invasives" = a MAP question → use `invasive.py` (or `s2.anomaly`) FIRST**,
   not `predict` alone. Don't answer a spatial "where" with only a corridor fraction.

## ✂️ ANSWER STYLE — short, honest, multi-turn (the product feel)

Give a ~2-minute, data-backed answer, THEN stop and offer follow-ups. Do NOT write a thesis.
- **TOOL BUDGET: aim for ~3–5 connector calls, then ANSWER.** Do NOT chain 10+ tools per question — pick the
  2–3 that most directly answer it, report, and offer the deeper checks as FOLLOW-UPS the user opts into.
  For multi-species questions (nursery / "which trees / which survive"): recommend a SHORTLIST from ecology +
  ONE batch call (e.g. `phenology.py --species-list`), don't exhaustively probe every species. Speed is a feature.
- **Lead with the finding in 2–4 sentences**, backed by real numbers + named sources.
- **Then offer 1–3 concrete follow-ups** the user can say yes to (this is how we go deeper, multi-turn):
  "I found N records nearby — transfer them via an SDM?" · "No local records, but papers say this occurs
  near hills and there ARE hills in your AOI — map them?" · "Climate looks suitable per an SDM — corroborate
  with satellite?" · "Want the high-res map to eyeball it?"
- **Be honest + always recommend the acquirable next data step** when scarce. Never fake specifics.
- **paper_data is a FIRST-CLASS origin.** For "where is X / what drives X", check `paper_data` for X's
  DRIVERS/COVARIATES (soil, elevation, rainfall, associated species), then map those covariates with
  satellite (landcover/terrain/s2). `/why` should name the paper.
- **Never hand-pick point sources.** Use the `points` resolver — `points.py get --species "<X>"` returns a
  cached CSV path merging **GBIF + iNaturalist + paper_data**. Cheaper/faster layers first; reach for
  high-res (skyfi/Maxar) only when the user asks or a follow-up needs it.

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

## "Where are the invasives / where is the Lantana?" — one command (any species)

You CANNOT ID a species from 10 m satellite, but you can build a free invasive-**likelihood** map and
narrow any paid spend to a few points. **Just run the `invasive` connector — it does the whole funnel:**
```
python /opt/data/connectors/invasive.py map --species "Lantana camara"     # or any invasive
```
→ writes a field-navigable HTML map + **GPS waypoints** (CSV/GeoJSON) to `/opt/data/work/invasive/<species>/`.
Under the hood (all FREE): (1) an **Earth-Engine RandomForest** trained on that species' RECENT GBIF
records (widens the search if sparse; falls back to phenology-only if <3 records) vs background, over a
6-band Sentinel-2 stack; (2) **multi-year stay-green phenology** (natives go bare in the dry season,
evergreen invaders stay green — require it two years running); likelihood = 0.6·RF + 0.4·persistence.
The building blocks, if you need them piecemeal: `s2.py anomaly_grid` (phenology), `embedding.py
similarity` (looks-like-known-presence), `occurrence.search` (validate).

**Then confirm at the top waypoints with high-res imagery (the tiny paid step):**
```
python /opt/data/connectors/skyfi.py best --bbox <w,s,e,n> --cap-usd 50   # prices a recent scene, budget-guarded
```
`skyfi.py` searches/prices/orders/downloads a SkyFi archive scene (order is refused above the cap and
dry-run unless --yes). Report the honest limit: the map is **likelihood, not a species ID** (evergreen
natives also stay green) — walk the waypoints or buy one scene to confirm; GPS a few patches to retrain.

**The principle generalises:** free/coarse data NARROWS (find candidates, decide where to spend), paid/fine
data CONFIRMS at those points. Apply it to any "where is X" free layers can't fully resolve.

**Whenever you TRANSFER a modelled signal onto a map (predict/RF/SDM, invasive, greening), OFFER the
ground-truth lens** — `groundtruth_lens.py` builds a static HTML showing every method's prediction (toggle)
with a cursor lens onto high-res imagery, so the user eyeballs what's actually there. **Concrete recipe for
"show me a lantana map I can check against the imagery":** (1) `invasive.py map --species "Lantana camara"`
(writes `/opt/data/work/invasive/lantana_camara/data.json`); (2) build the lens over the staged EBTL high-res
base (`/opt/data/work/gt/ebtl_base.jpg`, its extent is in `/opt/data/work/gt/ebtl_base.json` `bbox_wsen`):
`groundtruth_lens.py build --base /opt/data/work/gt/ebtl_base.jpg --bbox 78.176867,12.727863,78.190131,12.740135
--a1 /opt/data/work/invasive/lantana_camara/data.json --out /opt/data/work/gt/lens.html`; (3) give the user
the `lens.html` path. If no high-res base is staged, skip the lens and hand back the map + waypoints. It's the honest way to
present a transfer; reusable for "what grows here / where is X vs Y / is Y greening" too. For local points,
GBIF is research-grade-only (sparse); **iNaturalist direct has far more** (EBTL bbox: 218 obs vs ~0 GBIF).

## Species co-occurrence / colocation ("what grows/lives around X?")

A repeatable chain — don't hand-roll it:
1. **Find X** — `occurrence.search "<species X>" <aoi>` → X points (GBIF).
2. **Hypothesise co-occurring species** from the ecoregion + the land cover of X's points (`ecoregion`,
   `landcover`) — this list is DOMAIN KNOWLEDGE, so treat it as candidates to VERIFY, not fact.
3. **Confirm each candidate with data** (strongest → weakest):
   - `paper_data` **plot lists** = TRUE co-occurrence (same plot) — gold standard;
   - else **one call, by species name** (the resolver fetches + caches the points for you — do NOT create
     or name CSVs yourself): `geo.py cooccur --a-species "<X>" --b-species "<candidate>" --bbox <w,s,e,n>
     --radius-km 5` → how many candidate records sit near X (a shared-habitat PROXY, presence-only);
   - if occurrence is too sparse, **`predict` SDM-overlap**: model X and the candidate's suitability
     and overlap the suitable areas (shared *habitat*, even without co-located records).
4. **Report** the verified co-occurrences with the honest limit (proximity ≠ same-plot; presence-only).
Do NOT hand-compute distances or invent point-file names — `geo.cooccur --a-species/--b-species` fetches
via the `points` resolver (GBIF + iNaturalist, cached) and does the math (shows cleanly in /why).

## Verify species you name (don't assert from memory)

Whenever you name a **specific species** (e.g. "typical trees here are Anogeissus, Terminalia…"),
that's your KNOWLEDGE, not data. Either:
- (preferred) **verify it now** — one cheap `occurrence.search "<species>" <aoi>`: is it actually
  recorded here? Say "confirmed: N records" or "not recorded locally (may still occur)"; **or**
- **label it plainly** — "typical for this ecoregion, not verified at your site — want me to check?".
Prefer verifying (it's one call). The `/why` view flags anything unverified as inference.

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
when do X fruit / seeds to collect now / which mother trees": get the candidate native list (occurrence/
paper_data for the AOI) then **one parallel call** `phenology.py --species-list "A,B,C,D"` → ranks which are
**fruiting NOW** + the full calendar (do NOT call phenology per species — that times out). Single species:
`phenology.py --species "<sci name>"`. Then
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

When a land-cover CLASS is too coarse ("how DENSE is the canopy", "bare vs vegetated", fine
dry-season stress): `s2.py summary --bbox <aoi>` or `s2.py at --points sites.csv` gives **Sentinel-2
10 m NDVI** (canopy-density proxy) — finer than WorldCover classes / MODIS greenness. It does NOT
identify tree species (that needs hyperspectral: EMIT/Pixxel). **Use real data (S2 is free) rather
than only *suggesting* higher-res imagery.**

**Getting a species' points? Use the `points` resolver** — `points.py get --species "<name>" --bbox <w,s,e,n>`
returns a cached CSV path (merges GBIF + iNaturalist). NEVER invent a points filename; pass the returned path
(or use `--a-species/--b-species` on tools that support it). One source-of-truth for points; add a new source
by editing only `points.py`.

Available connectors: `landcover`, `fire`, `terrain`, `protected_areas`,
`occurrence`, `inaturalist`, `points`, `greenness`, `ecoregion`, `embedding`, `predict`, `hyperspectral`, `paper_data`,
`ebird` (needs a free key), `phenology`, `indicators`, `water`, `s2`, `geo`, `invasive` (one-command
invasive map, any species), `skyfi` (buy/download high-res imagery, budget-guarded), `groundtruth_lens`
(reusable verify map: multi-method prediction + cursor lens onto high-res). One card each here.
