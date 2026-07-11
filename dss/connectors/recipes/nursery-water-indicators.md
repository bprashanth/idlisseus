# Recipe: nursery / phenology · ponds / water · bioindicators

### Nursery / seed-collection ("which native to grow / when do X fruit / seeds now / mother trees")
Get the candidate native list (`points.get` / `paper_data` for the AOI) then **ONE parallel call**:
`phenology.py --species-list "A,B,C,D"` → ranks which are **fruiting NOW** + the calendar. Do NOT call
phenology per species (it times out). Single species: `phenology.py --species "<sci name>"`. Reason to the
**planting window** (Krishnagiri = NE monsoon ~Oct–Dec): collect seed at fruiting → propagate → plant at
monsoon. Pair with `points`/`occurrence` (is it near the site?), `terrain`/`landcover` (does the site suit
it?); flag drought-tolerant natives for dry scrub.

### Water / ponds ("which pond dries first / how much water do our ponds hold")
`water.py ponds --bbox <aoi>` ranks surface-water bodies by how EARLY they dry (JRC seasonality/occurrence,
30 m); or `water.py at --points ponds.csv` to annotate known ponds. Pair with `greenness` (dry-season
stress). Sub-30 m farm ponds may be missed → honest gap + field ask.

### Bioindicators ("which creatures signal a healthy forest / soil / water")
`indicators.py --concern <soil_health|forest_recovery|water_quality|pollination|connectivity> --bbox <aoi>`
→ the **sourced** bioindicator taxa (dung beetles, ants, butterflies, **spiders**, dragonflies…) + what
GBIF/iNat actually records near the site. Often the honest answer is "watch + survey these" (a concrete
ask). EBTL already tracks **arachnids** → `forest_recovery`.

### Canopy density (finer than land-cover class)
`s2.py summary --bbox <aoi>` or `s2.py at --points sites.csv` → Sentinel-2 10 m NDVI (canopy-density proxy),
finer than WorldCover / MODIS. It does NOT ID tree species (needs hyperspectral EMIT/Pixxel). Use real S2
data rather than only *suggesting* higher-res imagery.
