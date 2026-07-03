# connector: occurrence

- **purpose:** GBIF species occurrence records (public, no key).
- **when to use:** get where a species (e.g. Lantana camara) has been recorded, or
  what species are recorded in an area.
- **produces/annotates:** POINT **producer** — `search()` returns occurrence points.

**functions**
- `search(species, bbox=[w,s,e,n], limit=300, years=None) -> [{id,lat,lon,species,year,dataset}]`
- `species(bbox) -> (total_count, facets)`

**gotcha:** occurrence density reflects **sampling effort** (observers cluster near
roads/reserves), not true abundance. Good for presence / where-recorded; weak as
an absolute density. Pair with `landcover`/`geo` for context.

**example**
```
python /opt/data/connectors/occurrence.py search --species "Lantana camara" --bbox 76.3,10.2,77.2,11.6 --out lantana.csv
```
