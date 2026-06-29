# Climate–Fire Relationships Across Global Mountain Systems: A Six-Continent Analysis

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18421412.svg)](https://doi.org/10.5281/zenodo.18421412)

## Overview

This repository contains the Google Earth Engine code and processed datasets for analyzing climate–fire relationships across six global mountain systems using Landsat 8/9 imagery (2013–2023). The data support a panel regression analysis examining how temperature and precipitation influence fire severity across fuel-limited and climate-limited fire regimes.

## Repository Contents

```         
├── SM_Code_S1_GEE_Analysis.js          # Google Earth Engine analysis code
├── MountainFire_Himalayas_Central_2013_2023.csv
├── MountainFire_Rocky_Mountains_Central_2013_2023.csv
├── MountainFire_Andes_Central_2013_2023.csv
├── MountainFire_Alps_Western_2013_2023.csv
├── MountainFire_East_African_Highlands_2013_2023.csv
├── MountainFire_Australian_Alps_2013_2023.csv
└── README.md
```

## Study Regions

| Region | Geographic Extent | Fire Season | Observations |
|------------------|------------------|------------------|------------------|
| Central Himalaya | 83.0–88.0°E, 27.0–29.5°N | February–May | 38937 |
| Central Rockies | 108.0–104.0°W, 37.0–41.0°N | June–September | 67640 |
| Central Andes | 73.0–70.0°W, 14.0–11.0°S | June–October | 39958 |
| Western Alps | 6.0–8.5°E, 44.5–47.0°N | June–September | 39776 |
| East African Highlands | 36.5–38.5°E, 1.5°S–0.5°N | January–March | 23132 |
| Australian Alps | 147.5–149.5°E, 37.5–35.5°S | November–February | 19735 |

**Total observations:** 229,178 pixel-years across six continents (2013–2023)

## Data Description

### Sampling Design

-   **Spatial resolution:** 30 m (Landsat native resolution)
-   **Sampling grid:** 500 m systematic spacing (exceeds typical fire severity autocorrelation range)
-   **Temporal extent:** 2013–2023 (11 years)
-   **Panel structure:** Persistent pixel identifiers enable tracking of same locations across years

### Variable Descriptions

#### Identifiers

| Variable            | Description                                  | Type    |
|-----------------|----------------------------------------|---------------|
| `pixel_id`          | Persistent pixel identifier (region_lon_lat) | String  |
| `region`            | Study region name                            | String  |
| `year`              | Observation year                             | Integer |
| `fire_season_start` | Fire season start date (YYYY-MM-DD)          | Date    |

#### Fire Severity Metrics

| Variable | Description | Units/Range |
|------------------------|------------------------|------------------------|
| `dNBR` | Differenced Normalized Burn Ratio (primary outcome) | Continuous |
| `NBR_observed` | Observed fire-season median NBR | −1 to +1 |
| `NBR_predicted` | Harmonic model predicted NBR | −1 to +1 |
| `nbr_anomaly_zscore` | Standardized NBR anomaly (dNBR / RMSE) | Z-score |
| `burn_severity_class` | FIREMON severity classification | 0–4 |
| `burned_binary` | Binary burn indicator (dNBR ≥ 0.10) | 0/1 |

### Burn Severity Classes (FIREMON protocol)

| Class     | Value | dNBR Range | Interpretation               |
|-----------|-------|------------|------------------------------|
| Unburned  | 0     | \< 0.10    | No fire effect detected      |
| Low       | 1     | 0.10–0.27  | Minor vegetation mortality   |
| Moderate  | 2     | 0.27–0.44  | Mixed vegetation mortality   |
| High      | 3     | 0.44–0.66  | Substantial canopy mortality |
| Very High | 4     | ≥ 0.66     | Complete vegetation removal  |

#### Climate Variables (ERA5-Land)

| Variable               | Description                               | Units |
|------------------------|-------------------------------------------|-------|
| `temp_mean_C`          | Fire-season mean 2-m air temperature      | °C    |
| `temp_max_C`           | Fire-season maximum temperature           | °C    |
| `temp_range_C`         | Fire-season temperature range             | °C    |
| `precip_season_mm`     | Fire-season total precipitation           | mm    |
| `pet_season_mm`        | Fire-season potential evapotranspiration  | mm    |
| `water_balance_mm`     | Precipitation minus PET                   | mm    |
| `precip_antecedent_mm` | Pre-season precipitation (3 months prior) | mm    |
| `swe_preseason_mm`     | Pre-season snow water equivalent          | mm    |

#### Topographic Variables (SRTM 30-m)

| Variable          | Description                               | Units/Range |
|-----------------|---------------------------------------|-----------------|
| `elevation_m`     | Elevation above sea level                 | m           |
| `slope_deg`       | Terrain slope                             | degrees     |
| `northness`       | Cosine of aspect (south = −1, north = +1) | −1 to +1    |
| `eastness`        | Sine of aspect (west = −1, east = +1)     | −1 to +1    |
| `tpi_500m`        | Topographic Position Index (500-m radius) | m           |
| `heat_load_index` | Heat load index (McCune & Keon, 2002)     | 0 to 1      |

#### Auxiliary Variables

| Variable                 | Description                            | Units     |
|----------------------|----------------------------------|----------------|
| `harmonic_rmse`          | Harmonic model fit quality (RMSE)      | NBR units |
| `total_observations`     | Number of clear-sky Landsat scenes     | Count     |
| `landcover_class`        | ESA WorldCover land cover class        | Code      |
| `modis_burned_reference` | MODIS MCD64A1 burned area (validation) | 0/1       |

## Methods Summary

### Fire Severity Calculation

Fire severity was quantified using the differenced Normalized Burn Ratio (dNBR), calculated as the difference between a harmonic phenological baseline prediction and observed fire-season NBR:

```         
dNBR = NBR_predicted − NBR_observed
```

The harmonic model accounts for seasonal phenological variation:

```         
NBR(t) = β₀ + β₁t + β₂cos(2πt) + β₃sin(2πt) + β₄cos(4πt) + β₅sin(4πt) + ε
```

### Data Quality Filters

| Filter                | Threshold             | Rationale                      |
|---------------------|---------------------|-----------------------------|
| Minimum observations  | ≥ 30 clear-sky scenes | Robust harmonic model fitting  |
| Maximum harmonic RMSE | \< 0.50               | Excludes poor phenological fit |
| dNBR range            | −1.0 to 2.0           | Excludes implausible values    |

### Mountain Delineation

Mountain areas defined following UNEP-WCMC criteria (Kapos et al., 2000): - Elevation ≥ 2,500 m: classified as mountain regardless of slope - Elevation 1,500–2,500 m: classified if slope ≥ 2° - Elevation 1,000–1,500 m: classified if slope ≥ 5°

### Vegetation Mask

Analysis restricted to vegetated land covers (ESA WorldCover v200): - Tree cover (class 10) - Shrubland (class 20) - Grassland (class 30)

## Code Usage

### Requirements

-   Google Earth Engine account ([sign up](https://earthengine.google.com/signup/))
-   Access to Google Earth Engine Code Editor

### Running the Code

1.  Open the [Google Earth Engine Code Editor](https://code.earthengine.google.com)
2.  Create a new script and paste the contents of `SM_Code_S1_GEE_Analysis.js`
3.  Set `CURRENT_REGION_INDEX` (line 67) to select region:
    -   `0` = Central Himalaya
    -   `1` = Central Rockies
    -   `2` = Central Andes
    -   `3` = Western Alps
    -   `4` = East African Highlands
    -   `5` = Australian Alps
4.  Click **Run**
5.  In the **Tasks** tab, click the export task to save results to Google Drive

### Reproducing All Regions

Run the script six times, changing `CURRENT_REGION_INDEX` from 0 to 5, to generate all datasets.

## Data Sources

| Source | Description | Reference |
|------------------------|------------------------|------------------------|
| Landsat 8/9 Collection 2 | Surface reflectance imagery | Masek et al. (2020) |
| SRTM | 30-m digital elevation model | Farr et al. (2007) |
| ERA5-Land | Monthly climate reanalysis | Copernicus (2019) |
| ESA WorldCover | 10-m land cover classification | Zanaga et al. (2022) |
| MODIS MCD64A1 | Burned area product (validation) | Giglio et al. (2018) |

## References

Copernicus Climate Change Service. (2019). ERA5-Land monthly averaged data from 1950 to present [Dataset]. Copernicus Climate Change Service (C3S) Climate Data Store (CDS). <https://doi.org/10.24381/CDS.68D2BB30>

Farr, T. G., Rosen, P. A., Caro, E., Crippen, R., Duren, R., Hensley, S., Kobrick, M., Paller, M., Rodriguez, E., & Roth, L. (2007). The shuttle radar topography mission. Reviews of Geophysics, 45(2). <https://doi.org/10.1029/2005RG000183>

Giglio, L., Boschetti, L., Roy, D. P., Humber, M. L., & Justice, C. O. (2018). The Collection 6 MODIS burned area mapping algorithm and product. Remote Sensing of Environment, 217, 72–85. <https://doi.org/10.1016/j.rse.2018.08.005>

Kapos, V., Rhind, J., Edwards, M., Price, M. F., & Ravilious, C. (2000). Developing a map of the world's mountain forests. In M. F. Price & N. Butt (Eds.), Forests in sustainable mountain development: A state of knowledge report for 2000 (pp. 4–19). CABI Publishing. <https://doi.org/10.1079/9780851994468.0004>

Key, C. H., & Benson, N. C. (2006). Landscape assessment (LA). In D. C. Lutes, R. E. Keane, J. F. Caratti, C. H. Key, N. C. Benson, S. Sutherland, & L. J. Gangi, FIREMON: Fire effects monitoring and inventory system (Gen. Tech. Rep. RMRS-GTR-164-CD, pp. LA-1–55). USDA Forest Service, Rocky Mountain Research Station.

Masek, J. G., Wulder, M. A., Markham, B., McCorkel, J., Crawford, C. J., Storey, J., & Jenstrom, D. T. (2020). Landsat 9: Empowering open science and applications through continuity. Remote Sensing of Environment, 248, 111968. <https://doi.org/10.1016/j.rse.2020.111968>

McCune, B., & Keon, D. (2002). Equations for potential annual direct incident radiation and heat load. Journal of Vegetation Science, 13(4), 603–606. <https://doi.org/10.1111/j.1654-1103.2002.tb02087.x>

Zanaga, D., Van De Kerchove, R., Daems, D., De Keersmaecker, W., Brockmann, C., Kirches, G., Wevers, J., Cartus, O., Santoro, M., Fritz, S., Lesiv, M., Herold, M., Tsendbazar, N.-E., Xu, P., Ramoino, F., & Arino, O. (2022). ESA WorldCover 10 m 2021 v200 (v200) [Dataset]. Zenodo. <https://doi.org/10.5281/ZENODO.7254221>

Zhu, Z., & Woodcock, C. E. (2014). Continuous change detection and classification of land cover using all available Landsat data. Remote Sensing of Environment, 144, 152–171. <https://doi.org/10.1016/j.rse.2014.01.011>

## License

This work is licensed under a [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).

You are free to: - **Share** — copy and redistribute the material in any medium or format - **Adapt** — remix, transform, and build upon the material for any purpose

Under the following terms: - **Attribution** — You must give appropriate credit, provide a link to the license, and indicate if changes were made.

## Contact

**Anukram Adhikary (**<https://orcid.org/0000-0001-6236-6196>)\
Postdoctoral Research Scholar\
Department of Forestry and Environmental Resources\
North Carolina State University\
Raleigh, NC, USA

*Last updated: January 2026*
