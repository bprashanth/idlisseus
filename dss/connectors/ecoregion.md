# connector: ecoregion

- **purpose:** RESOLVE Ecoregions 2017 — which ecoregion/biome a place sits in, and
  sampling analog points in the same ecoregion elsewhere.
- **when to use:** (1) onboarding a new AOI — name its ecoregion; (2) the
  **analog-transfer harder mode** — pull points from the same ecoregion *outside*
  the AOI so an out-of-AOI correlation can be reported honestly.
- **produces/annotates:** POINT annotator — adds `ecoregion`, `biome`.

**functions**
- `at(points) -> + ecoregion, biome`
- `covering(bbox=[w,s,e,n]) -> [{ecoregion, biome}]`
- `analog_points(eco_name, exclude_bbox, n) -> points in the same ecoregion, outside the AOI`

**legend/bands:** RESOLVE `ECO_NAME`, `BIOME_NAME` (owned).

**example**
```
python /opt/data/connectors/ecoregion.py covering --bbox 77.95,12.30,78.45,12.80
```

**gotchas:** ecoregion polygons are coarse — a point near a boundary can fall in a
neighbour. `analog_points` returns points anywhere in the (possibly large)
ecoregion; pair with landcover/other filters if you need a like-for-like analog.
Always tag analog results `aoi_status: analog_ecoregion` in the answer.
