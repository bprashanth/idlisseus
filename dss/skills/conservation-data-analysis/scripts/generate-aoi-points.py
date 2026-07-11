# Point Generation for Geospatial Analysis

**Purpose**: Generate random sample points within a bounding box for connector analyses (landcover, greenness, occurrence).

---

## Usage

```python
import csv
import random

def generate_points(w, s, e, n, count=100, out_path='/opt/data/work/points.csv'):
    """Generate random lat/lon points within a bbox."""
    points = []
    for _ in range(count):
        lon = random.uniform(w, e)
        lat = random.uniform(s, n)
        points.append({'lat': lat, 'lon': lon})
    
    with open(out_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['lat', 'lon'])
        writer.writeheader()
        writer.writerows(points)
    
    return out_path

# Example: EBTL site
generate_points(78.170, 12.721, 78.197, 12.747, count=100)
```

---

## Notes

- **100 points** is typically sufficient for site-level analysis (~2-3 km AOI).
- For larger regions, increase to 200-500 points.
- Points are uniformly distributed; no stratification by terrain/landcover.
- Output CSV format: `lat,lon` (required by connectors).

---

## Example Output

```csv
lat,lon
12.73929192865249,78.19159199672097
12.742142284916502,78.19241736335674
...
```

**Tip**: Always verify the generated points visually (e.g., overlay on satellite imagery) to ensure they fall within the intended AOI.