# connector: embedding

- **purpose:** Google AlphaEarth Satellite Embedding (64-d, 10 m, annual) — the
  *similarity* primitive: how alike two places are across everything the model saw.
- **when to use:** restoration convergence ("is the site becoming more like intact
  reference forest?"), site matching, change that a single index (NDVI) misses.
- **produces/annotates:** POINT annotator — `similarity()` adds `embed_sim` (cosine
  to a reference); `similarity_trend()` adds `sim_start,sim_end,sim_slope,converging`.

**functions**
- `similarity(points, ref=[lat,lon], year=2023) -> + embed_sim` (cosine 0..1)
- `similarity_trend(points, ref=[lat,lon], years='2019-2024') -> converging/stable/diverging`

**legend/bands:** 64 unit-norm bands `A00..A63`; cosine = dot product. ~0.85 = very
alike (forest vs forest), ~0.5 = unlike (city vs forest).

**example**
```
python /opt/data/connectors/embedding.py similarity_trend --points sites.csv --ref 12.60,78.05 --years 2019-2024
```

**gotchas:** the embedding mixes structure/phenology/moisture — high similarity means
"looks alike to the model", not a named variable. The **reference defines the target**;
pick a genuinely intact patch, and ideally average several references (a single ref can
itself change over time and skew a trend).
