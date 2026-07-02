# Corpus — gold datasets, connectors, distractors

Working list for the broker experiment. Scoped to the S. India AOI: Valparai /
Anamalai / Nilgiris / Gudalur / Kotagiri. Status: **confirmed** = URL + file
types verified this session; **known** = well-known public API; **gap** = still
to find.

## Gold assets (static files — `type: asset`)

| ID | Dataset | Source | Files | AOI | Serves Q |
|----|---------|--------|-------|-----|----------|
| A5a | Long-term woody-stem census, 2 one-ha plots 2017–2022 (Manamboli mature TR forest 10.358N 76.890E; Candura secondary Valparai 10.309N 76.834E) | Zenodo [10426971](https://zenodo.org/records/10426971) | 7×CSV + README + R (**confirmed**) | Anamalai/Valparai | 1,3 (restoration plots) |
| A5b | Mixed-native seedling **survival** across 5 restoration sites, 2001–2006 (planting records, survival by canopy) | Zenodo [10630501](https://zenodo.org/records/10630501) | CSV + README + figs (**confirmed**) | Valparai/Anamalai | 1,3 (survival/intervention) |
| A5c | Restoration opportunities: 105 canopy-gradient plots + 19 reference rainforest | Zenodo [10692141](https://zenodo.org/records/10692141) | verify files | Western Ghats | 1,3 (habitat context) |
| A7a | Mammal occurrence records 2025–26, central & southern Western Ghats (EpiCollect5) | Zenodo [18923778](https://zenodo.org/records/18923778) | verify files | Western Ghats | 3 (species obs) |
| A1a | Manar estate vegetation survey, S. Nilgiris — 70 nested plots, **includes Lantana camara** | GBIF `ncf-nrp-manar-vegetation-2024` (DwC-A) | Darwin Core zip | S. Nilgiris | 2,4 (lantana occ) |
| A7b | PCQ tree plots, Valparai/Anamalai rainforest fragments | GBIF `anamalai-trees-pcqdata` (DwC-A) | Darwin Core zip | Valparai/Anamalai | 3 (trees/species) |

| A6 | **Lantana removal experiment** — Mudumalai TR (Nilgiris/AOI), 2 sites × 48 plots (5×5 m), treatments **Cut / Uproot / Control**, initial biomass per 1×1 m quadrat, Feb 2012–May 2013, rainfall gradient | Prasad/Sundaram/Hiremath 2018, *Biol. Invasions* [10.1007/s10530-018-1785-1](https://link.springer.com/article/10.1007/s10530-018-1785-1); manuscript at [White Rose 134358](https://eprints.whiterose.ac.uk/id/eprint/134358/) | PDF (**downloaded** `assets/2018_Prasad_lantana_eradication.pdf`) | Mudumalai | 2 (removal) |
| A9 | Restoration beyond degraded forests (canopy gradient, coffee/invasive context) — literature asset | Osuri et al. 2024, *Biol. Conservation* 291:110519 | PDF (**downloaded** `assets/2024_Osuri_restoration_beyond_degraded.pdf`) | Western Ghats | 3 (native/literature) |

**A6 note:** the raw plot table is **not** openly deposited (Springer supp only /
not on Dryad-Zenodo) — so A6 is a *text/paper* asset, not a CSV. That is useful:
it tests whether cards built from prose (methods describing plot-level removal)
retrieve as well as cards built from structured data.

**Remaining nice-to-haves (not blockers):**
- **A1 dedicated lantana occurrence** — Manar survey (A1a) covers it, but a
  GBIF Lantana-camara occurrence download clipped to the AOI would be cleaner.
- More NCF papers for a richer A9 literature pool — can bulk-pull to `~/data/`
  on request.

## Connectors (live APIs — `type: connector`)

Hermes calls these itself; the card is a capability pointer, not stored data.

| ID | Layer | Connector | Status |
|----|-------|-----------|--------|
| A2 | Active fire detections | **NASA FIRMS** — also in Earth Engine (`FIRMS`) | known; EE path tested |
| A3 | 10 m land cover | **ESA WorldCover** — in Earth Engine (`ESA/WorldCover/v200`) | known; EE path tested |
| A4 | Protected-area boundaries | **Protected Planet / WDPA** API | known; to wire |
| — | Elevation / terrain | Earth Engine `USGS/SRTMGL1_003` | **confirmed** (1518 m @ Nilgiris pt) |
| — | Species occurrence at scale | GBIF API | known |

**Earth Engine is authenticated (project `plantwars`) and covers fire + land
cover + terrain in one connector** — this collapses A2/A3 into EE scripts. FIRMS
and WorldCover need not be separate connectors unless we want to test the
non-EE API path too. Protected Planet + GBIF are the separate connectors to add.

## Distractors (`type: asset`/`connector`, NOT in any gold answer)

Target **25–40**. Purpose: make top-k selective so recipe differences show. Mix
of (a) wrong domain, (b) wrong geography, (c) adjacent-but-irrelevant. Build the
cards from real Zenodo/GBIF records where possible so the text is realistic.

Categories + examples:
- **Wrong domain, same region:** soil carbon / SOC plots; groundwater &
  hydrology; air quality; agricultural crop yield; pollinator surveys;
  rainfall/climate station records; coffee/cardamom plantation yield.
- **Right domain, wrong geography:** Himalayan forest plots; Eastern Ghats
  lantana modelling; Amazon restoration; African savanna fire; Australian FIRMS
  fire; European WDPA protected areas; boreal land cover.
- **Adjacent-but-irrelevant:** marine/coral biodiversity; mangrove extent;
  glacier mass balance; urban land use (Bangalore); night-lights; population
  census; road networks; digital elevation of a different continent.
- **Near-miss traps (hardest):** a fire dataset for a *different* Indian state;
  a species-occurrence set with **no** invasives; a protected-area list with no
  boundaries (attributes only); a land-cover product at coarse 300 m resolution.

The near-miss traps are the most valuable — they test whether cards encode the
*distinguishing* attributes (geography, resolution, presence of invasives), not
just the topic.

## Refined question set

Kept close to NOTES; each gets an expected-reasoning note for the "explain your
choice" step. Gold IDs reference the table above.

1. **Which areas are most exposed to forest fire near restoration sites?**
   Gold: A2 (fire), A5a/A5b (restoration plots → site coords), A3 (land cover/fuel).
   Reasoning: plots give intervention locations; FIRMS gives disturbance; land
   cover gives fuel context; needs spatial join; cannot infer fire *cause*.
2. **Where should we prioritize lantana removal?**
   Gold: A1a (lantana occurrence), A6 (removal history — *gap*), A3 (land cover).
   Reasoning: where lantana is now × where already removed × proximity to
   fields/plantations.
3. **Are restored plots showing recovery in native species?**
   Gold: A5a/A5b (plots + survival), A7a/A7b (species obs), A9 (literature → what
   is "native").
   Reasoning: need plot definition + a native-species list compiled from
   observations + literature.
4. **Compare invasive records inside vs outside protected areas.**
   Gold: A1a (lantana), A4 (protected-area boundaries).
   Reasoning: overlay occurrence on WDPA boundaries; same rough region; broker
   returns boundaries or an EE/GBIF script, not points.
5. **Is fire risk higher in scrub or plantation land cover?**
   Gold: A2 (fire), A3 (land cover).
   Reasoning: join FIRMS points to WorldCover classes; both are API/EE calls, so
   the broker must retrieve the right *connector* per AOI.

## Notes on what's confirmed vs assumed

- A5a, A5b file formats verified this session (CSV + README codebook = ideal
  asset cards; README doubles as the codebook the recipes can mine).
- Earth Engine connector verified end-to-end (auth + real query).
- A5c, A7a file lists not yet opened — verify before ingesting.
- GBIF DwC-A records (A1a, A7b) are real datasets; download format is Darwin
  Core zip (standard, parseable).
