# EBTL Invasive Species Profile

**Site**: Elephants by the Lake (EBTL), Krishnagiri, Tamil Nadu  
**Coordinates**: ~12.735N, 78.184E  
**Site bbox**: 78.170–78.197E, 12.721–12.747N  
**Donor belt**: 76.0–79.5E, 11.0–13.6N (wider dry-deccan region)

---

## Invasives Confirmed AT EBTL Site

| Species | Common Name | Records at Site | Closest Distance | Notes |
|---------|-------------|-----------------|------------------|-------|
| **Jatropha gossypiifolia** | Bellyache Bush | 1 | 0.6 km | Inside site bbox |
| **Dichrostachys cinerea** | Sicklebush | 1 | 1.0 km | Inside site bbox |
| **Abrus precatorius** | Rosary Pea / Crab's Eye | 1 | ~2 km | Inside site bbox |

---

## Invasives in Surrounding Region (within 50 km)

| Species | Common Name | Total Records (donor belt) | Within 10 km | Within 50 km | Closest Record |
|---------|-------------|---------------------------|--------------|--------------|----------------|
| **Lantana camara** | Lantana / Tickberry | 300 | 0 | 11 | 20.7 km |
| **Parthenium hysterophorus** | Congress Grass | 300 | 0 | 14 | 14.7 km |
| **Opuntia stricta** | Erect Prickly Pear | 112 | 0 | 12 | 14.7 km |
| **Prosopis juliflora** | Mesquite / Velikkuvel | 110 | 0 | 1 | 38.9 km |
| **Chromolaena odorata** | Siam Weed | N/A (SSL error) | ? | ? | ? |

---

## Key Observations

1. **Low immediate invasive pressure**: The core EBTL site has only 3 invasive records, all from opportunistic iNaturalist observations rather than systematic surveys.

2. **Lantana is nearby but not at site**: Despite 300 records in the donor belt, the closest Lantana is ~21 km away. This is unusual — Lantana typically invades dry deciduous forests aggressively. Possible explanations:
   - EBTL site may have natural barriers (topography, water sources)
   - Management interventions may be keeping it out
   - Sampling bias (iNaturalist observations cluster around roads/access points)

3. **Jatropha and Dichrostachys are the primary concerns**: These two species are already inside the site. Both are known to:
   - Colonise disturbed areas and gaps
   - Compete with native regeneration
   - Spread along edges (roads, farm boundaries, grazing paths)

4. **Data limitation**: These are iNaturalist research-grade observations, not a systematic botanical survey. A field survey would likely find more invasives, especially at edges and disturbed patches.

---

## Management Implications

- **Priority 1**: Control Jatropha and Dichrostachys at the site level before they establish seed banks
- **Priority 2**: Monitor edges for Lantana incursion — it's within 20 km and could arrive via wind, animals, or human activity
- **Priority 3**: Establish a baseline survey (plot-level) to detect invasives early

---

## Data Sources

- iNaturalist research-grade observations via GBIF API
- Site landcover: ESA WorldCover v200 (10m resolution, 500 sample points)
- Distance calculations: Haversine formula from site center (12.73394, 78.18344)

---

## Related Files

- `scripts/compute-invasive-distances.py` — Script to compute distances from site center to invasive occurrence points
- `references/south-deccan-natives.md` — Native species pool for comparison
