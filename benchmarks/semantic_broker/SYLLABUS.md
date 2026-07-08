# Syllabus — s2 + colocation stress test (2026-07-06)

12 field-worker questions chosen to exercise **Sentinel-2 (canopy/phenology)** and the
**colocation skill** (where is X relative to Y; what co-occurs with X), plus elephants/birds/
inventory/scarcity. Each has a **rubric**: the connectors a good answer uses, the honest framing
it must have, and a **research-grounded expectation** (so we can tell a real answer from a fluent
guess). Questions are phrased the way Varun types (plain, <15 words). Used by `bench/model_skill_bench.py`.

Legend for rubric scoring (from `/why` + answer text):
`site-scale` = answered at the ~2.9 km EBTL site, not the 100 km corridor, and SAID which ·
`grounded` = pulled real data (named source) not memory · `verified-species` = any named species was
checked against occurrence/paper, or labelled unverified · `honest-caveat` = named the limit + a data ask ·
`used-skill` = used the intended connector/skill (s2 / geo.cooccur / predict.route / ebird) not hand-rolled.

---

### Q1. is lantana taking over our forest? *(invasives / s2)*
- **connectors:** occurrence(Lantana, site+corridor) → s2.summary/at (canopy density where it is) → predict.route (spread).
- **expectation:** Lantana thrives in **open/disturbed dry-deciduous understory** (Bandipur studies: dense thickets suppress native regeneration & carbon). A good answer ties occurrence to low-canopy/edge S2 and gives a modelled spread fraction with the honest "corridor records, not a site census."
- **win:** site-scale + s2 used + honest modelled-not-observed.

### Q2. what always grows near lantana? *(colocation — the headline case)*
- **connectors:** occurrence(Lantana) → hypothesise from ecoregion+landcover → occurrence(candidate)+geo.cooccur, and/or paper_data plot lists → predict SDM-overlap fallback.
- **expectation (Bandipur/S-India dry deciduous):** teak *Tectona grandis*, amla *Phyllanthus emblica*, *Stereospermum*, *Schrebera*, bamboo in moister strips. Lantana is an **understory invader** of these deciduous stands. The honest answer: proximity of records = shared-habitat **proxy**, true co-occurrence needs plot lists.
- **win:** verified-species (each named tree checked) + geo.cooccur used (not hand-rolled) + proxy caveat.

### Q3. show me where the lantana is on our land *(the free MAP)*
- **connectors:** s2 phenology-anomaly (stays-green in dry season) → AlphaEarth similarity to known Lantana points → GBIF validation → map.
- **expectation:** we cannot ID a species from 10 m NDVI; the honest deliverable is an **invasive-LIKELIHOOD** map (dry-season stay-green anomaly, confirmed by similarity to known presence), with "buy a 3 m Planet scene at the top candidates to confirm" as the next step.
- **win:** produced a candidate map + labelled it likelihood-not-ID + named the cheap confirm step.

### Q4. which birds tell me our forest is getting healthier? *(birds / indicators)*
- **connectors:** ebird(hotspot L36453021) → guild/indicator breakdown → indicators.py forest_recovery.
- **expectation:** frugivores/insectivore guild share + understory specialists signal recovery; EBTL already logs arachnids (forest_recovery indicator). Honest: need a **pre-clearing baseline** for a trend.
- **win:** grounded in real eBird community + honest "no baseline = no trend yet" + monitoring ask.

### Q5. where do the birds and the fruiting trees overlap? *(cross-taxa colocation)*
- **connectors:** ebird dispersers/frugivores points → occurrence(fruiting natives) → geo.cooccur → landcover/s2 habitat.
- **expectation:** frugivore-dense spots near fruiting trees = **seed-rain hotspots** (also where Lantana spreads — birds disperse it). Bridge birds→plants via diet.
- **win:** used geo.cooccur across taxa + the disperser bridge + honest proxy.

### Q6. what do the elephants here eat? *(elephants / verify from data)*
- **connectors:** occurrence(Elephas maximus, corridor) for presence; paper_data for diet; verify named food plants against occurrence.
- **expectation (Sukumar, Nilgiri):** diet **~85% grass / ~15% browse**, more browse in dry season; *Tamarindus indica* & *Acacia* frequent in dung. A good answer states the grass-dominant split, names food plants **and verifies** which are actually recorded locally, honest that diet is from literature not a site study.
- **win:** verified-species + literature-labelled + grass/browse split correct.

### Q7. where do elephants and birds overlap, and what grows there? *(user's example — multi-taxa)*
- **connectors:** occurrence(elephant) + ebird points → geo.cooccur → landcover/s2 of the overlap → occurrence/paper for the plants there.
- **expectation:** overlap likely in mosaic edge/water-adjacent habitat; "what grows there" answered from landcover class + S2 density + any local plant records, honestly proxy.
- **win:** chained colocation → habitat → plants, site-scale, honest.

### Q8. what trees do we have and how thick is the canopy across our land? *(forest inventory / s2)*
- **connectors:** s2.summary (%dense canopy) + landcover class breakdown + occurrence(trees at site) + paper_data plot inventory.
- **expectation:** EBTL is dry-deciduous restoration → patchy canopy, mostly sparse/scrub with denser strips; species list from GBIF+paper is thin at site scale → the honest inventory is "here's canopy density + what's recorded, send plot data for a real inventory."
- **win:** s2 density number at site-scale + honest thin-inventory + plot-data ask.

### Q9. which native seeds should I collect now, and do those trees grow near us? *(nursery + colocation)*
- **connectors:** phenology(fruiting month) → occurrence(species near site) → colocation/geo to confirm proximity.
- **expectation:** July = collect species fruiting now; cross-check they're actually recorded near EBTL (verify-species) before recommending; plant at NE monsoon (Oct–Dec). Flag drought-tolerant natives for dry scrub.
- **win:** phenology used + verified the trees occur locally + seasonal reasoning.

### Q10. which of our ponds dries up first, and what's around it? *(water + colocation cross-correlate)*
- **connectors:** water.ponds (JRC seasonality) → s2/greenness dry-season stress around it → landcover/occurrence of surroundings.
- **expectation:** rank ponds by early-dry; surroundings from landcover + S2. Honest: sub-30 m farm ponds may be missed → field ask.
- **win:** water used + surroundings characterised + honest resolution gap.

### Q11. is our forest actually coming back? *(open / cross-correlate)*
- **connectors:** greenness.trend (NDVI slope) + s2 density + landcover change.
- **expectation:** multi-year NDVI slope = recovery signal; S2 adds fine density; honest that satellite greenness ≠ native-vs-invasive (Lantana greens too — ties back to Q1/Q3).
- **win:** trend grounded + the Lantana-greens-too honesty + site-scale.

### Q12. what data are we missing to answer all this well? *(scarcity / scout)*
- **connectors:** meta — reflect on gaps surfaced across Q1–Q11; name concrete acquirable datasets.
- **expectation:** the recurring asks — plot inventories / absence points (for the invasive-map RF), a 3 m Planet scene at candidate points, structured eBird effort, pond field truth. This question **feeds the Scout**.
- **win:** concrete, prioritised, acquirable data asks (not vague "more data").
