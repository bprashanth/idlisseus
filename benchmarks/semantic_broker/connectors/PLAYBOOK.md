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
3. **Group / rank** with pandas. This part is yours.

## Rules

- **Never write raw Earth Engine reducer code.** Call the connector.
- **Never guess a class code or band name.** Run the connector's `--describe` to
  get the legend, or read its card.
- Connectors take a CSV of points and return a CSV of points with new columns.

## Invoke (CLI)

```
python /opt/data/connectors/<name>.py --describe
python /opt/data/connectors/<name>.py <function> --points in.csv --out out.csv
```

Available connectors: `landcover`, `fire`, `terrain`, `protected_areas`,
`occurrence`, `geo`. One card each in this folder.
