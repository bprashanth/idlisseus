# connector: geo

- **purpose:** pure-python spatial joins between two point/polygon sets (no API).
- **when to use:** proximity or containment between *asset* data — e.g. lantana
  points ↔ cropland/fields, sites ↔ fire points, points ↔ supplied reserve polygons.
- **produces/annotates:** POINT annotator over asset data.

**functions**
- `nearest(points, others) -> + nearest_dist_km, nearest_id`
- `buffer_count(points, others, radius_km) -> + n_within`
- `cooccur(a, b, radius_km) -> SUMMARY: n_b, n_b_within_radius_of_a, frac_near, mean_nearest_km`
- `within(points, polygons_geojson) -> + inside, poly_name`

**colocation:** `cooccur` is the "do X and Y occur together?" summary — how many of point-set B sit within
`radius_km` of set A + the mean nearest distance. It's the checked tool for the co-occurrence skill
(don't hand-roll distances). **Proximity of presence records = shared-habitat PROXY, not true
co-occurrence** — confirm with `paper_data` plot lists (same-plot) or `predict` SDM-overlap.

**gotcha:** distances are great-circle km (fine for landscape-scale ranking);
`within()` uses outer rings only (ignores holes). Use `within` with a supplied
GeoJSON when WDPA lacks the boundary (see `protected_areas` coverage note).

**example**
```
python /opt/data/connectors/geo.py nearest --points lantana.csv --others fields.csv --out lantana_near.csv
python /opt/data/connectors/geo.py cooccur --a lantana.csv --b pterocarpus.csv --radius-km 5
python /opt/data/connectors/geo.py within --points occ.csv --polygons reserves.geojson
```
