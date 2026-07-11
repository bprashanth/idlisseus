# connector: fire

- **purpose:** MODIS MOD14A1 active fire / thermal anomalies.
- **when to use:** rank locations by fire exposure, or get fire locations in a region.
- **produces/annotates:** POINT annotator — `exposure()` adds `fire_count`,
  `fire_density`. Also `points()` produces fire locations.

**functions**
- `exposure(points, radius_km=5, years="2020-2025") -> + fire_count, fire_density`
- `points(bbox=[w,s,e,n], years) -> [{lat,lon,fire_days}]`

**metric:** `fire_count` = sum of pixel-fire-days in the buffer over the period;
`fire_density` = per km². Good for **ranking**, not an absolute burned area.

**gotcha:** ~1 km resolution — use `radius_km >= 3`. Wet evergreen sites
legitimately return ~0 (they don't burn); that is a real signal, not an error.

**example**
```
python /opt/data/connectors/fire.py exposure --points sites.csv --radius-km 5 --years 2020-2025
```
