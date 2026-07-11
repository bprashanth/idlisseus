# Connectors (reference)

You have connectors for live geospatial data in `/opt/data/connectors/`. Use them instead of
writing Earth Engine code yourself.

## Pattern
1. Get points — a CSV with `lat`,`lon`, or `occurrence.py search --species "<name>" --bbox w,s,e,n`.
2. Annotate — run the connector that adds the column you need (it takes a points CSV, returns points).
3. Group / rank with pandas.

## Invoke
```
python /opt/data/connectors/<name>.py --describe            # see its functions + legend
python /opt/data/connectors/<name>.py <function> --points in.csv --out /opt/data/work/out.csv
```
Write `--out` files under `/opt/data/work/` (mkdir -p it). Connector/input folders are read-only; if
`--out` can't be written the connector prints the CSV to stdout instead — capture it.

## Available connectors
`landcover`, `fire`, `terrain`, `protected_areas`, `occurrence`, `greenness`, `ecoregion`,
`embedding`, `predict`, `hyperspectral`, `paper_data`, `ebird` (needs a free key), `phenology`,
`indicators`, `water`, `s2`, `geo`. Run each one's `--describe` for its functions and legend.

## Rules
- Never guess a class code or band name — run `--describe` first.
- Connectors take a CSV of points and return a CSV of points with new columns.
