# connector: geo

- **purpose:** pure-python spatial joins between two point/polygon sets (no API).
- **when to use:** proximity or containment between *asset* data — e.g. lantana
  points ↔ cropland/fields, sites ↔ fire points, points ↔ supplied reserve polygons.
- **produces/annotates:** POINT annotator over asset data.

**functions**
- `nearest(points, others) -> + nearest_dist_km, nearest_id`
- `buffer_count(points, others, radius_km) -> + n_within`
- `within(points, polygons_geojson) -> + inside, poly_name`

**gotcha:** distances are great-circle km (fine for landscape-scale ranking);
`within()` uses outer rings only (ignores holes). Use `within` with a supplied
GeoJSON when WDPA lacks the boundary (see `protected_areas` coverage note).

**example**
```
python /opt/data/connectors/geo.py nearest --points lantana.csv --others fields.csv --out lantana_near.csv
python /opt/data/connectors/geo.py within --points occ.csv --polygons reserves.geojson
```
