# indicators — bioindicator taxa for an ecological concern (GBIF-grounded)

- **produces:** for a concern, the **sourced** indicator taxa + what GBIF records near the site.
- **why:** small, surveyable taxa signal larger change. Turns "which insects show the soil is
  improving?" into the right groups to watch + what data exists + a concrete survey request.

**functions**
- `indicators(concern, bbox, years=None) -> per-taxon {gbif_records_near_site, indicates, citation}`
- concerns: `soil_health` · `forest_recovery` · `water_quality` · `pollination` · `connectivity`

**example**
```
python /opt/data/connectors/indicators.py --concern soil_health --bbox 78.170,12.721,78.197,12.747
python /opt/data/connectors/indicators.py --concern forest_recovery --bbox <aoi>   # butterflies, spiders
```

**gotchas:** the taxon→indicator links are **cited ecology, not our claim**; the counts are GBIF
(real, effort-biased, sparse at small sites). Usual honest output = "watch + survey these" (dung-beetle
pitfall traps, butterfly transects, spider quadrats). EBTL already tracks arachnids → `forest_recovery`.
Pair with `occurrence` (trend over years), `ebird` (bird indicators/dispersers), `phenology`.
