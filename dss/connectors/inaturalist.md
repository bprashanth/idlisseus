# inaturalist — species points from iNaturalist (open, no key)

- **purpose:** occurrence points from iNaturalist — far richer locally than GBIF research-grade (EBTL bbox: 218 obs / 97 plants vs ~0 GBIF for Lantana).
- **produces:** POINT producer, same schema as `occurrence`: `search(species, bbox) -> [{id,lat,lon,species,year,dataset}]`.
- **when:** local points where GBIF is sparse. **Prefer `points.py`** (merges GBIF+iNat, caches) — this is the iNat-only source it wraps.

**functions**
- `search(species, bbox=[w,s,e,n], limit=500, quality=None|'research')`

**example**
```
python /opt/data/connectors/inaturalist.py search --species "Lantana camara" --bbox 78.170,12.721,78.197,12.747
```
**gotcha:** no key; casual-grade included by default (`quality='research'` to restrict); paginates ~2000 max.
