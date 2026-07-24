# connector: terrain

- **purpose:** SRTM 30 m elevation, slope, aspect.
- **when to use:** add terrain covariates to points (fire and invasion both track
  slope/elevation), or characterise a site.
- **produces/annotates:** POINT annotator — adds `elevation` (m), `slope` (deg),
  `aspect` (deg).

**functions**
- `at(points) -> + elevation, slope, aspect`

**example**
```
python /opt/data/connectors/terrain.py at --points sites.csv --out sites_terrain.csv
```
