# phenology — flowering/fruiting calendar from GBIF (no key)

- **produces:** per-species **fruiting & flowering months** + per-month counts — the nursery's
  seed-collection timing, data-grounded (GBIF/iNaturalist `reproductiveCondition` annotations),
  works for ANY species (dry-deciduous or wet).
- **why:** restoration is supplied by a nursery; a nursery needs seed when it's available. This
  turns "when do jamun/neem fruit so we can collect seeds?" into a real answer.

**functions**
- `phenology(species, country='IN') -> {fruiting_months, flowering_months, fruiting_by_month, n_annotated, caveat}`

**example**
```
python /opt/data/connectors/phenology.py --species "Syzygium cumini"   # jamun -> fruiting May-Jun
python /opt/data/connectors/phenology.py --species "Azadirachta indica" # neem
```

**nursery chain:** fruiting months (collect seed) → propagate → plant at the site's monsoon
(Krishnagiri ≈ NE monsoon Oct–Dec). Pair with `occurrence` (near the site?), `terrain`/`landcover`
(site suitability), `paper_data`/traits (seed size, dispersal, drought tolerance).

**gotchas:** crowd-sourced & observer-biased; check `n_annotated` (needs enough annotated records
for a stable signal). Common names accepted for a few natives (jamun, neem, tamarind, amla, arjun…);
otherwise pass the scientific name. Report peak months + sample size, not a definitive calendar.
