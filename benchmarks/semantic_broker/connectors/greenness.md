# connector: greenness

- **purpose:** MODIS MOD13Q1 NDVI **trend over time** — is a place gaining or
  losing vegetation across years.
- **when to use:** recovery / degradation questions — "are restored plots greening
  up?", "which sites are recovering vs flat vs declining?". The TREND primitive:
  the one that needs *time*, not a single map value.
- **produces/annotates:** POINT annotator — adds `ndvi_start`, `ndvi_end`,
  `ndvi_slope` (NDVI change per year), `trend_class` (greening / flat / declining).

**functions**
- `trend(points, years='2019-2024') -> + ndvi_start, ndvi_end, ndvi_slope, trend_class`

**legend/bands:** MOD13Q1 `NDVI` band, ×0.0001 scale (owned). `trend_class`:
greening if slope > 0.005, declining if < -0.005, else flat. Run `--describe` for
the metric definition.

**example**
```
python /opt/data/connectors/greenness.py trend --points sites.csv --years 2019-2024 --out sites_ndvi.csv
```

**gotchas:** 250 m pixels — a plot smaller than ~6 ha shares its cell with
surroundings. NDVI saturates over dense canopy, so a mature intact forest reads
**high-and-flat** (not "failing to recover"); read `trend_class` together with
`ndvi_end`. Good for *ranking* recovery, not absolute biomass.
