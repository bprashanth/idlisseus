# connector: landcover

- **purpose:** ESA WorldCover v200 (10 m) land cover.
- **when to use:** you need the land-cover class *at* points, or the area per
  class in a region.
- **produces/annotates:** POINT annotator — adds `landcover` (class name) and
  `landcover_code`.

**functions**
- `classify(points) -> points + landcover, landcover_code`
- `area_by_class(bbox=[w,s,e,n]) -> {class_name: km2}`

**legend** (or run `--describe`)
`10 Tree cover · 20 Shrubland · 30 Grassland · 40 Cropland · 50 Built-up ·
60 Bare/sparse · 70 Snow/ice · 80 Water · 90 Herbaceous wetland · 95 Mangroves ·
100 Moss/lichen`

**gotcha:** there is **no plantation / tea / coffee class**. Plantations appear as
`Tree cover` or `Cropland`. For plantation extent use the land-use / restoration
assets, not this connector. (This is the trap v-1 Q5 fell into — it invented a
"plantation" class and mislabelled Built-up as Shrubland.)

**example**
```
python /opt/data/connectors/landcover.py classify --points sites.csv --out sites_lc.csv
python /opt/data/connectors/landcover.py area_by_class --bbox 76.3,10.2,77.2,11.6
```
