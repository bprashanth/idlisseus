#!/usr/bin/env python3
"""Generate a self-contained Iris dashboard HTML with Chart.js visualisations.

Reads iris.csv (stdlib csv), computes per-species stats, produces dashboard.html
with four inline charts loaded from https://cdn.jsdelivr.net/npm/chart.js
"""

import csv
import json
import math
import sys

CSV_PATH = "/opt/data/iris.csv"
HTML_PATH = "/opt/data/dashboard.html"


def read_csv(path):
    """Return list of dicts from CSV."""
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def species_counts(rows):
    """Count rows per species."""
    counts = {}
    for r in rows:
        s = r["species"]
        counts[s] = counts.get(s, 0) + 1
    # sort by species name for stable order
    return dict(sorted(counts.items()))


def summary_stats(rows, column):
    """Compute min, max, mean, std, median, count for a numeric column."""
    vals = []
    for r in rows:
        v = float(r[column])
        vals.append(v)
    n = len(vals)
    if n == 0:
        return {}
    mean = sum(vals) / n
    sorted_vals = sorted(vals)
    if n % 2 == 0:
        median = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
    else:
        median = sorted_vals[n // 2]
    variance = sum((x - mean) ** 2 for x in vals) / n
    std = math.sqrt(variance)
    return {
        "count": n,
        "min": round(min(vals), 3),
        "max": round(max(vals), 3),
        "mean": round(mean, 3),
        "median": round(median, 3),
        "std": round(std, 3),
    }


def per_species_stats(rows, column):
    """Return dict of {species: summary_stats} for a column."""
    species_groups = {}
    for r in rows:
        s = r["species"]
        species_groups.setdefault(s, []).append(float(r[column]))
    result = {}
    for s, vals in species_groups.items():
        n = len(vals)
        mean = sum(vals) / n
        sorted_vals = sorted(vals)
        if n % 2 == 0:
            median = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        else:
            median = sorted_vals[n // 2]
        variance = sum((x - mean) ** 2 for x in vals) / n
        result[s] = {
            "min": round(min(vals), 3),
            "max": round(max(vals), 3),
            "mean": round(mean, 3),
            "median": round(median, 3),
            "std": round(math.sqrt(variance), 3),
        }
    return result


def build_scatter_data(rows):
    """Build per-species arrays for scatter plot (petal_length vs petal_width)."""
    species_order = []
    species_data = {}
    seen = set()
    for r in rows:
        s = r["species"]
        if s not in seen:
            seen.add(s)
            species_order.append(s)
            species_data[s] = {"x": [], "y": []}
        species_data[s]["x"].append(float(r["petal_length"]))
        species_data[s]["y"].append(float(r["petal_width"]))

    datasets = []
    colors = {"setosa": "#e63946", "versicolor": "#457b9d", "virginica": "#2a9d8f"}
    for s in species_order:
        d = species_data[s]
        datasets.append({
            "label": s,
            "data": [{"x": d["x"][i], "y": d["y"][i]} for i in range(len(d["x"]))],
            "backgroundColor": colors.get(s, "#888"),
        })
    return datasets


def build_histogram_data(vals, bins=10):
    """Build histogram bins from numeric values."""
    if not vals:
        return {"labels": [], "data": []}
    min_v = min(vals)
    max_v = max(vals)
    width = (max_v - min_v) / bins or 1
    bin_counts = [0] * bins
    bin_labels = []
    for i in range(bins):
        lo = min_v + i * width
        hi = lo + width
        bin_labels.append(f"{lo:.1f}-{hi:.1f}" if i < bins - 1 else f"{lo:.1f}+")

    for v in vals:
        idx = min(bins - 1, int((v - min_v) / width))
        bin_counts[idx] += 1

    return {"labels": bin_labels, "data": bin_counts}


def generate_html(rows):
    counts = species_counts(rows)
    species_list = list(counts.keys())
    count_values = list(counts.values())

    # scatter datasets
    scatter_datasets = build_scatter_data(rows)

    # sepal length histogram
    sepal_vals = [float(r["sepal_length"]) for r in rows]
    hist = build_histogram_data(sepal_vals, bins=10)

    # summary stats table
    columns = ["sepal_length", "sepal_width", "petal_length", "petal_width"]
    stats_rows = {}
    for col in columns:
        stats_rows[col] = summary_stats(rows, col)

    # per-species stats for display
    species_stats = {}
    for col in columns:
        species_stats[col] = per_species_stats(rows, col)

    # Build HTML
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Iris Dataset Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:system-ui,sans-serif; background:#f8f9fa; padding:20px; }}
  .container {{ max-width:1200px; margin:0 auto; }}
  h1 {{ margin-bottom:12px; color:#1a1a2e; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
  .card {{ background:#fff; border-radius:10px; padding:16px; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
  .card h2 {{ font-size:1rem; margin-bottom:8px; color:#333; }}
  .card canvas {{ width:100%; height:auto; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.85rem; }}
  th,td {{ padding:6px 10px; text-align:right; border-bottom:1px solid #e0e0e0; }}
  th {{ background:#f0f0f0; font-weight:600; }}
  td:first-child {{ text-align:left; font-weight:500; }}
  .species-table {{ margin-top:20px; }}
  .species-table th {{ background:#e8e8e8; }}
  caption {{ text-align:left; font-weight:600; margin-bottom:6px; font-size:0.95rem; }}
  .footer {{ margin-top:16px; text-align:center; font-size:0.8rem; color:#888; }}
</style>
</head>
<body>
<div class="container">
  <h1>📊 Iris Dataset Dashboard</h1>
  <p style="margin-bottom:16px;color:#555;">Built from iris.csv &mdash; {total_rows} samples, {species_count} species</p>

  <div class="grid">

    <!-- Bar chart: species counts -->
    <div class="card">
      <h2>Species Count</h2>
      <canvas id="barChart" width="400" height="300"></canvas>
    </div>

    <!-- Scatter: petal length vs petal width -->
    <div class="card">
      <h2>Petal Length vs Width (by species)</h2>
      <canvas id="scatterChart" width="400" height="300"></canvas>
    </div>

    <!-- Histogram: sepal length -->
    <div class="card">
      <h2>Sepal Length Distribution</h2>
      <canvas id="histChart" width="400" height="300"></canvas>
    </div>

    <!-- Summary stats table -->
    <div class="card">
      <h2>Summary Statistics</h2>
      <table>
        <thead><tr><th>Feature</th><th>Count</th><th>Mean</th><th>Std</th><th>Min</th><th>Max</th><th>Median</th></tr></thead>
        <tbody>
""".format(total_rows=len(rows), species_count=len(species_list))

    # stats table rows
    for col in columns:
        s = stats_rows[col]
        html += f"""          <tr><td>{col}</td><td>{s['count']}</td><td>{s['mean']}</td><td>{s['std']}</td><td>{s['min']}</td><td>{s['max']}</td><td>{s['median']}</td></tr>\n"""

    html += """        </tbody>
      </table>
    </div>
  </div>

  <!-- Per-species detail table -->
  <div class="card species-table">
    <h2>Per-Species Feature Means</h2>
    <table>
      <thead>
        <tr><th>Species</th>
"""

    for col in columns:
        html += f"<th>{col}<br><small>mean</small></th>"

    html += """        </tr></thead>
      <tbody>
"""

    for s in species_list:
        html += f"        <tr><td>{s}</td>"
        for col in columns:
            html += f"<td>{species_stats[col][s]['mean']}</td>"
        html += "</tr>\n"

    html += """      </tbody>
    </table>
  </div>

  <div class="footer">Generated by gen_dashboard.py &mdash; Chart.js via CDN</div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function () {
  // ---- Bar Chart: Species Counts ----
  const barLabels = """ + json.dumps(species_list) + """;
  const barData   = """ + json.dumps(count_values) + """;
  new Chart(document.getElementById('barChart'), {
    type: 'bar',
    data: { labels: barLabels, datasets: [{ label: 'Count', data: barData,
      backgroundColor: ['#e63946','#457b9d','#2a9d8f'] }] },
    options: { responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true }, x: {} } }
  });

  // ---- Scatter Chart: Petal Length vs Width ----
  const scatterDatasets = """ + json.dumps(scatter_datasets) + """;
  const scatterColors = ['#e63946','#457b9d','#2a9d8f'];
  scatterDatasets.forEach((ds, i) => {
    ds.borderColor = scatterColors[i]; ds.borderWidth = 0; ds.pointRadius = 4;
  });
  new Chart(document.getElementById('scatterChart'), {
    type: 'scatter',
    data: { datasets: scatterDatasets },
    options: { responsive: true,
      plugins: { legend: { display: true, position: 'top' } },
      scales: {
        x: { title: { display: true, text: 'Petal Length (cm)' } },
        y: { title: { display: true, text: 'Petal Width (cm)' } }
      } }
  });

  // ---- Histogram: Sepal Length ----
  const histLabels = """ + json.dumps(hist['labels']) + """;
  const histData   = """ + json.dumps(hist['data']) + """;
  new Chart(document.getElementById('histChart'), {
    type: 'bar',
    data: { labels: histLabels, datasets: [{ label: 'Count', data: histData,
      backgroundColor: '#457b9d' }] },
    options: { responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true }, x: {} } }
  });
});
</script>
</body>
</html>"""

    with open(HTML_PATH, "w") as f:
        f.write(html)

    print(f"Dashboard written to {HTML_PATH}")


if __name__ == "__main__":
    rows = read_csv(CSV_PATH)
    generate_html(rows)
