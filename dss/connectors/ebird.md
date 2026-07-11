# ebird — eBird bird observations + hotspots (LOGIN connector)

- **produces:** POINT producer — bird occurrence points at a hotspot or in an area; plus
  `hotspot_info` (coords + species count) that can **anchor a site**.
- **auth:** needs a **free eBird API key** (web pages are bot-protected). Key resolution:
  env `EBIRD_API_KEY` → `~/.hermes/secrets/ebird.json` → `~/.config/idlisseus/ebird.json`
  (`{"api_key":"..."}`). Get one at https://ebird.org/api/keygen. `configured()` reports
  whether it's set; unset → the connector warns loudly and does nothing.

**functions**
- `hotspot_info(loc_id) -> {name, lat, lon, n_species}` — EBTL hotspot = **L36453021**
- `observations(loc_id=.., back=30) -> bird points at a hotspot`
- `observations(bbox=[w,s,e,n], back=30) -> bird points in an area` (eBird caps radius at 50 km)
- `species_list(loc_id) -> species recorded`

**example**
```
python /opt/data/connectors/ebird.py hotspot --loc L36453021
python /opt/data/connectors/ebird.py obs --loc L36453021 --back 30 --out /opt/data/work/birds.csv
```

**gotchas:** free key required (Dryad-pattern login connector). eBird `recent` is last-N-days
only and **effort-biased** (birders visit accessible spots; presence-lean, no true absence) —
pair with acoustic-hardware monitoring for unbiased site coverage (see `ebtl/DATA_GAPS.md`).
Finer than GBIF for a specific hotspot/site.
