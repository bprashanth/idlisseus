# water — surface-water bodies & how long they hold water (JRC GSW, GEE)

- **produces:** distinct waterbodies near a site RANKED by dries-first (JRC Global Surface Water
  seasonality/occurrence/recurrence, 30 m, 1984-2021); or annotate known ponds with those metrics.
- **why:** answers "which pond dries first?" (low seasonality) and "how reliable is this water?"
  with real hydrology — not a greenness proxy.

**functions**
- `ponds(bbox) -> waterbodies ranked dries-first {area_ha, seasonality_months, occurrence_pct, recurrence_pct, centroid}`
- `at(points) -> annotate known ponds with seasonality/occurrence/recurrence`

**example**
```
python /opt/data/connectors/water.py ponds --bbox 78.15,12.70,78.22,12.77
python /opt/data/connectors/water.py at --points ponds.csv --out /opt/data/work/ponds_water.csv
```

**gotchas:** historical satellite record (long-run pattern, NOT this year's level) — validate with
field notes; sub-30 m farm ponds under-detected (honest gap → field ask). Pair with `greenness`
(dry-season stress) and `terrain` (catchment).
