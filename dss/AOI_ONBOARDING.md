# Onboarding a new AOI — the replication playbook

What happens when a new user/site joins. Each step lists **what we do**, **the concrete EBTL
example** (so it's replayable), and **where the code is**. The goal: go from "here's roughly my
land" to "a system that answers grounded questions about it + knows what data to go get."

---

## Step 0 — Resolve the AOI to precise geometry
**Do:** take the user's indication (place name, Plus Code, a pin, a boundary file) and resolve it to
a tight bbox/polygon. Distinguish **site** (the actual parcel) from **corridor/region** (context) —
answers must be about the parcel, not a 100 km region.
**EBTL:** the project's address carried a Plus Code `7J4WP5MM+H9` → decoded to **12.7339 N,
78.1834 E**; we set `site_bbox ≈ [78.170, 12.721, 78.197, 12.747]` (~2.9 km) + a wider
`corridor_bbox` + a `dry_deccan_donor_bbox`. eBird hotspot **L36453021** independently confirmed the
coordinates. Stored in `benchmarks/algebra/aois/elephants_by_the_lake/site.json` + the agent-facing
`connectors/SITE_EBTL.json`.
**GAP / TODO:** today the AOI is **pre-seeded by hand** (one JSON per site). Generalize with a
**geocode/AOI-resolver connector** (place/Plus-Code/latlon → bbox via free OSM Nominatim) or a
per-user site profile, so no manual seeding is needed.

## Step 1 — Characterize the AOI (what KIND of place is it?)
**Do:** pull ecoregion, climate, land cover, terrain. This sets the *transfer rules*: you can only
borrow data from places that are similar in the right sense (appearance / climate / ecoregion).
**EBTL:** ecoregion = **South Deccan Plateau dry-deciduous / thorn** (near Eastern Ghats), ~800 mm
rainfall — crucially **NOT** the wet Western Ghats where most Indian ecology data comes from. That
mismatch is why naive transfer fails and why we retargeted everything to the dry-Deccan.
**Code:** `connectors/ecoregion.py`, WorldClim (`predict._worldclim`), `landcover.py`, `terrain.py`.

## Step 2 — Census the data (the "axis of maximum data reliance")
**Do:** for the AOI, count what each source actually returns — GBIF occurrence, eBird, paper_data,
etc. Find which data type is **abundant** (your bridge/hook) and which is **scarce** (your gaps).
**EBTL:** at the tight site — **birds ABUNDANT** (eBird hotspot: 136 species) but **plants/mammals
~0** (0 GBIF Lantana, 0 elephant *in the bbox*; 43/53 only across the 100 km corridor). So birds are
the axis of maximum reliance; plants/invasives are the scarcity to bridge toward.
**Code:** `occurrence.py` (GBIF), `ebird.py`, `paper_data.search`.

## Step 3 — Ingest a corpus (get more data)
**Do:** crawl papers/datasets relevant to the AOI's ecoregion. Strategies (all in DATA_STRATEGIES):
curated community → author-graph → broad theme keyword **retargeted to the ecoregion** → authenticated
sources (Dryad). Parse xlsx/zip/relational files; extract georeferenced points; keep a **catalog**
(card corpus) even for non-georeferenced studies.
**EBTL:** grew **17 → 256 datasets** (author-graph off NCF + dry-Deccan theme search + Dryad login).
Honest finding: only ~66 India-relevant, ~657 dry-Deccan-belt points, ~2 in the site bbox → **crawling
harder does NOT fix site scarcity; it's structural** → lean on transfer + occurrence firehoses (GBIF).
**Code:** `benchmarks/algebra/research/paper_crawl.py`, `paper_data.py`.

## Step 4 — Index for discovery (make buried data findable)
**Do:** build per-study **data cards** (title + all columns + codebook definitions + value types) and
retrieve over them (keyword pre-filter → embeddings top-k → LLM re-rank). Buried data (a wildfire
study's `prosopis` column) becomes findable.
**EBTL:** 140→169 cards; retrieval bench — embeddings/hybrid ≈ 0.91 semantic, one-prompt-LLM degrades
at scale. **Code:** `benchmarks/algebra/discovery/`.

## Step 5 — Per question: route the answer (transfer / bridge / answer)
**Do:** `gate` the AOI vs available data (AlphaEarth NN-analog + WorldClim MESS), then `route` →
**overlap** (use observed), **transfer_rf** (AlphaEarth-analog), **sdm_climate** (climate-analog,
cross-ecoregion within envelope), or **refuse→collect**. When direct data is scarce, **bridge** via
the abundant dataset + known ecology. Match method to question type; NEVER force species modelling on
human-use questions; NEVER return empty.
**EBTL:** dry-Deccan Lantana → EBTL = valid climate transfer; wet-Valparai → EBTL = refuse. Birds →
frugivore dispersers → Lantana-spread signal (bridge) despite 0 plant records.
**Code:** `predict.py` (gate/route/sdm_climate/transfer), `ebird.frugivore_dispersers`, PLAYBOOK skill.

## Step 6 — Turn every gap into a data request
**Do:** where the honest answer is "not enough data," name the concrete acquirable thing.
**EBTL asks:** higher-res hyperspectral (Pixxel ~5 m) for invasive mapping; acoustic bird hardware
(AudioMoth+BirdNET) for unbiased site birds; eBird habitat logging; dung-beetle/community surveys.
**Code:** `benchmarks/algebra/ebtl/DATA_GAPS.md`, `ROADBLOCKS.md` (account/paywall blocks).

---

## AOI expansion — the "greedy data search" (how we go from one site to a searchable landscape)

A user supplies **one** AOI (the parcel). To model a data-starved parcel we must **widen outward
to where borrowable data exists** — but every widened AOI must be *derived, cited, and overridable*,
never fabricated. This is what the **Scout** does (`components/scout.py`), and it's the reproducible
replacement for ad-hoc model judgment.

**Procedure (pseudocode):**
```
onboard(aoi_hint):
  site      = geocode(aoi_hint)                    # coords/bbox — CITE the geocoder (Plus Code, OSM…)
  ecoregion = ecoregion.at(site); climate = worldclim(site)
  mission   = read_org_clues(aoi_hint)             # web-fetch the org's own page → flagship species /
                                                   # stated goals ("elephants","corridor"). CITE the URL.
  # GREEDY EXPANSION — widen until data is usable (the "dotted-line AOI"):
  box = site
  while gbif_density(box) < USABLE and box < MAX:
      box = widen(box toward the mission clue)      # e.g. a NAMED corridor from a CITED atlas
  corridor = box   # tag: derived-by-density + cited source + "geometry APPROXIMATE if no shapefile"
  analog_sites = same_ecoregion_reserves(ecoregion) # known reserves; VERIFY each by real GBIF count
  sources = search(GBIF, eBird, Zenodo, CKAN, data.gov.in, paper_data)  # VERIFY rows>0; stamp provenance
  return {site, corridor(cited,approx), analog_sites(verified), sources(stamped)}
```

**EBTL (verified, not invented):** the corridor `[77.4,11.9,78.5,12.9]` = the real **WII/WTI Elephant
Corridors of India 2023** atlas (Hosur–Dharmapuri) — cited in `aois/elephants_by_the_lake.json`
(`wii_corridors`, flagged "no open shapefile → request from WII / digitize"). The **bbox was set by
widening the 0.5° property box until GBIF density was usable: 37k → 1.72M records.** Analog reserves
verified by GBIF count (Bandipur-Mudumalai 892k, Sathyamangalam-BRT 508k, Cauvery/MM Hills 326k).
`data.gov.in` was queried and returned **0 hits** (recorded as attempted-empty, not used).

**Anti-hallucination guards (protect every future AOI):** each derived AOI / source must carry
(a) **how it was derived**, (b) a **citation or "VERIFIED n rows"**, (c) an **approximate/phantom
flag** when geometry or data is soft, (d) be **overridable** by the user. The Scout already does the
"phantom guard" (found-but-0-rows is flagged, never admitted) + provenance stamps; extend that to the
*derived AOIs themselves*. **Never present a widened AOI/number without its lineage.**

**User-facing disclosure template** (so choices never look hallucinated):
> "You gave me the ~70-acre site. To find enough data to model it, I widened outward: read EBTL's
> mission (elephants, corridor restoration), matched it to the WII/WTI corridor atlas
> (Hosur–Dharmapuri), and expanded the box until GBIF had usable density (37k→1.7M). I also pulled 3
> same-ecoregion reserves for borrowable data. The corridor geometry is approximate (no open shapefile
> — flagged); you can narrow or replace any of these."

## The bootstrap infra (what runs onboarding — don't re-derive these)
- **`components/loop.py`** — the AOI bootstrap tick (orchestrator).
- **`components/scout.py`** — data-frontier discovery: GBIF/eBird/Zenodo/CKAN + analog-ecoregion,
  verifies rows, stamps provenance, phantom-guard.
- **`components/proposer.py` + `controller.py`** — turn the AOI's weighted buckets into a question
  curriculum + question bank.
- **`components/miner.py`** — mines run logs into permanent playbook rules (`playbook_rules.md`).
- **`research/`** — the crawl (`paper_crawl.py`), KB (`kb.py`), discovery loop (`loop.py`, `autoloop.py`).

### Onboarding checklist (for the next AOI)
- [ ] AOI geometry resolved (site vs corridor) — *automate the geocode step*
- [ ] ecoregion + climate + landcover characterized
- [ ] data census done → abundant axis + scarce gaps identified
- [ ] corpus crawled (ecoregion-retargeted) + cataloged
- [ ] cards + retrieval built
- [ ] transfer algebra validated (gate says what's transferable)
- [ ] data requests drafted for the scarce axes
