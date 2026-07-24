# South Deccan Plateau Dry Deciduous Forests — Native Species Pool

**Ecoregion**: South Deccan Plateau dry deciduous forests  
**Biome**: Tropical & Subtropical Dry Broadleaf Forests  
**Typical Bbox**: 76.0–79.5°E, 11.0–13.6°N (Bandipur/BRT/Mudumalai/Cauvery/Hosur corridor)

## Verified Native Species (with occurrence records in region)

| Scientific Name | Common Name | Records in Corridor | Notes |
|-----------------|-------------|---------------------|-------|
| *Tectona grandis* | Teak | 16+ | Dominant canopy species in dry deciduous forests |
| *Vitex altissima* | Tree Vitex | 12+ | Strong co-occurrence with Lantana (11/12 within 5 km) |
| *Pterocarpus marsupium* | Malabar Kino | 11+ | Important timber species, 6/11 near Lantana |
| *Anogeissus latifolia* | Dhon | 7+ | 3/7 records near Lantana, common in dry forests |
| *Lagerstroemia parviflora* | Crape Myrtle | 6+ | **Strongest co-occurrence signal** (6/6 within 5 km, mean 1.1 km) |
| *Dalbergia latifolia* | Indian Rosewood | 2+ | Rare in occurrence data, 1/2 near Lantana |

## Landcover Context for Lantana in This Region

Lantana camara occurrence points show mixed landcover association:
- **Cropland** (~35%): Edge habitats, disturbed areas
- **Tree cover** (~30%): Forest interiors, canopy gaps
- **Built-up** (~25%): Human-modified landscapes
- **Grassland/Shrubland** (~10%): Open habitats

## Co-occurrence Analysis Method

To find species growing near a target (e.g., Lantana):

1. **Get target points**: `occurrence.py search --species "<target>" --bbox <region>`
2. **Get candidate points**: `occurrence.py search --species "<candidate>" --bbox <region>`
3. **Compute proximity**: `geo.py cooccur --a target.csv --b candidate.csv --radius-km 5`
   - `frac_near`: Fraction of candidate records within 5 km of target
   - `mean_nearest_km`: Average distance to nearest target point
4. **Rank**: Higher `frac_near` + lower `mean_dist` = stronger shared-habitat signal

**Caveat**: Proximity = shared habitat proxy, NOT same-plot co-occurrence. For verified plot-level data, check `paper_data` or run field surveys.

## Typical Dry Deciduous Canopy Species (to hypothesize candidates)

- *Anogeissus latifolia* (Dhon)
- *Terminalia tomentosa* (White Teak)
- *Tectona grandis* (Teak)
- *Pterocarpus marsupium* (Malabar Kino)
- *Dalbergia latifolia* (Rosewood)
- *Lagerstroemia parviflora* (Crape Myrtle)
- *Manilkara hexandra* (Mimusops)
- *Flacourtia montana* (Karam)
- *Grewia tilaefolia*
- *Vitex altissima* (Tree Vitex)

## Data Gaps

- **Ground-truth plot data**: Limited paper_data coverage for this specific ecoregion
- **Fine-scale occurrence**: iNaturalist has more records than GBIF for some species
- **Seasonal dynamics**: Phenology data needed for fruiting/flowering windows

## References

- PLAYBOOK.md: Species co-occurrence pattern (section "Species co-occurrence / colocation")
- geo.py: `cooccur` function for proximity analysis
- occurrence.py: Species presence searches
- paper_data.py: Plot-level verified data from research papers
