# Invasive Species Mapping and Visualization Guide

## Overview

This document provides guidance on creating maps and visualizations for invasive species data at ecological restoration sites, particularly for the "Elephants by the Lake" (EBTL) project.

## Data Sources

- **On-site occurrences**: `/opt/data/work/ebtl_all_occurrences.csv` — iNaturalist/GBIF records within the EBTL site bbox
- **Regional occurrences**: `/opt/data/work/lantana_donor.csv` — donor belt records for regional context (e.g., Lantana camara)
- **Site boundaries**: EBTL site bbox: `78.170, 12.721, 78.197, 12.747` (WSEN)

## Map Types

### 1. On-site Invasive Distribution Map

Shows invasive species records within the site boundary with:
- Site boundary (dashed green rectangle)
- Individual occurrence points with species labels and year
- Nearby regional records (faded markers to show context)
- Scale bar and grid lines for orientation

**Use case**: Field staff need to know where invasives are actually recorded on-site.

### 2. Habitat Profile Analysis

Computes environmental conditions where invasives occur:
- Elevation distribution
- Slope preference (flat/gentle/moderate/steep)
- Land cover mix (natural vs. human-modified)
- Aspect bias (if any)

**Use case**: Understanding what drives invasive distribution to inform management priorities.

### 3. Proximity Analysis

Computes distances from invasive records to:
- Site center
- Site boundary
- Other invasives
- Key features (roads, water bodies, villages)

**Use case**: Prioritizing control efforts based on proximity to sensitive areas.

## Visualization Techniques

### SVG Maps (Pure Python)

When matplotlib is unavailable or installation is blocked, use pure Python to generate SVG maps:

```python
import math, csv

# Define map bounds and projection
def lon_to_x(lon, map_w, map_e, svg_w):
    return int((lon - map_w) / (map_e - map_w) * svg_w)

def lat_to_y(lat, map_s, map_n, svg_h):
    return int((map_n - lat) / (map_n - map_s) * svg_h)

# Build SVG string manually
lines = []
lines.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 650">')
# Add elements: rect, circle, text, line, etc.
lines.append('</svg>')

# Write to HTML wrapper
html = f'<html><body>{"".join(lines)}</body></html>'
with open('output.html', 'w') as f:
    f.write(html)
```

**Advantages**:
- No external dependencies (works in any browser)
- Full control over styling and labels
- Lightweight (few KB)
- Interactive when opened in browser (zoom, pan)

### Color Coding

Use consistent colors for species across maps:
- **Jatropha gossypiifolia**: `#d62728` (red)
- **Dichrostachys cinerea**: `#ff7f0e` (orange)
- **Abrus precatorius**: `#9467bd` (purple)
- **Lantana camara**: `#e67300` (dark orange)
- **Site boundary**: `#2d5a27` (green)

### Legend Design

Include:
1. Species symbols with colors
2. Site boundary representation
3. Scale bar (10 km is standard for regional maps)
4. Brief annotations (e.g., "EBTL Site (~70 ac)")

## Analysis Patterns

### Pattern 1: On-site vs. Regional Comparison

```python
# Filter on-site records
site_invasives = [r for r in all_records if in_bbox(r, site_bbox)]

# Filter regional records within X km
nearby = [r for r in all_records if haversine_km(site_center, r) < 50]

# Compare counts and spatial distribution
```

### Pattern 2: Temporal Trends

Extract year from occurrence records and analyze:
- First recorded presence
- Frequency over time
- Recent vs. historical records

```python
from collections import Counter
years = [int(r['year']) for r in records if r.get('year')]
year_counts = Counter(years)
```

### Pattern 3: Distance to Features

```python
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# Compute distance from each invasive point to site center
for inv in invasives:
    dist = haversine_km(site_cy, site_cx, inv['lat'], inv['lon'])
    inv['distance_km'] = dist
```

## Pitfalls

- **Don't over-interpret sparse data**: Single-observation records (like Jatropha at EBTL) may be pioneers or misidentifications. Field verification needed.
- **Lantana may be under-recorded on-site**: iNaturalist bias toward accessible areas; systematic surveys often find more.
- **Don't present proximity as causation**: Nearby Lantana records show regional presence, not direct spread to site.
- **Label data scale clearly**: "Satellite-scale (10m resolution)" vs. "Plot-level (field survey)".

## Output Format

When delivering maps:
1. Save as HTML file (SVG embedded) for easy browser viewing
2. Provide absolute path: `/opt/data/work/<filename>.html`
3. Summarize key findings in text:
   - Number of records per species
   - Spatial distribution (on-site vs. edge vs. outside)
   - Temporal patterns (if multiple years)
   - Management implications

## Example Workflow

```python
# 1. Load occurrence data
import csv
with open('/opt/data/work/ebtl_all_occurrences.csv') as f:
    records = list(csv.DictReader(f))

# 2. Filter for invasives of interest
invasives = ['Jatropha gossypiifolia', 'Dichrostachys cinerea', 'Abrus precatorius']
site_invasives = [r for r in records if r['species'].strip().strip('"') in invasives]

# 3. Generate map (SVG)
# ... (see SVG generation code above)

# 4. Save and report
path = '/opt/data/work/ebtl_invasives_map.html'
with open(path, 'w') as f:
    f.write(html_content)

print(f"Map saved to {path}")
print(f"Records: {len(site_invasives)} on-site invasives")
```

## Related Skills

- `conservation-data-analysis` — Main workflow for ecological data analysis
- `ecoregion-analysis` — Regional context and native species pools
- `field-survey-planning` — Ground-truthing and plot design
