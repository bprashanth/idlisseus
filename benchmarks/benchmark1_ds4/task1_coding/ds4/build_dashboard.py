#!/usr/bin/env python3
"""
Download tips.csv and generate a self-contained dashboard.html
with Plotly charts: scatter (bill vs tip colored by smoker),
bar (avg tip% by day), and distribution (tip by gender).
"""
import csv
import json
import urllib.request
import os

# 1. Download dataset
url = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv"
csv_path = "/tmp/tips.csv"
urllib.request.urlretrieve(url, csv_path)

# 2. Parse CSV
rows = []
with open(csv_path, newline="") as f:
    reader = csv.DictReader(f)
    for r in reader:
        r["total_bill"] = float(r["total_bill"])
        r["tip"] = float(r["tip"])
        r["size"] = int(r["size"])
        rows.append(r)

# 3. Compute aggregates

# 3a. Scatter data – split by smoker
scatter_smoker_no  = {"x": [], "y": [], "text": []}
scatter_smoker_yes = {"x": [], "y": [], "text": []}
for r in rows:
    d = scatter_smoker_yes if r["smoker"] == "Yes" else scatter_smoker_no
    d["x"].append(r["total_bill"])
    d["y"].append(r["tip"])
    d["text"].append(f"{r['day']} {r['time']}")

# 3b. Avg tip % by day
day_groups = {}  # day -> list of tip_pct
for r in rows:
    d = r["day"]
    tip_pct = r["tip"] / r["total_bill"] * 100
    day_groups.setdefault(d, []).append(tip_pct)

days_order = ["Thur", "Fri", "Sat", "Sun"]
avg_tip_pct = {d: sum(v)/len(v) for d, v in day_groups.items()}
bar_x = [d for d in days_order if d in avg_tip_pct]
bar_y = [avg_tip_pct[d] for d in bar_x]

# 3c. Tip distribution by gender
gender_male   = [r["tip"] for r in rows if r["sex"] == "Male"]
gender_female = [r["tip"] for r in rows if r["sex"] == "Female"]

# 4. Build Plotly HTML
html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tips Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.35.0.min.js" charset="utf-8"></script>
<style>
body { font-family: sans-serif; margin: 20px; background: #f8f9fa; }
h1 { text-align: center; color: #333; }
.plot-container { background: white; margin: 20px 0; padding: 10px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
</style>
</head>
<body>
<h1>🍽️ Restaurant Tips Dashboard</h1>
<div class="plot-container"><div id="scatter"></div></div>
<div class="plot-container"><div id="bar"></div></div>
<div class="plot-container"><div id="box"></div></div>

<script>
// ---------- Scatter: total_bill vs tip, colored by smoker ----------
const traceNo = {
  x: """ + json.dumps(scatter_smoker_no["x"]) + """,
  y: """ + json.dumps(scatter_smoker_no["y"]) + """,
  text: """ + json.dumps(scatter_smoker_no["text"]) + """,
  mode: 'markers',
  type: 'scatter',
  name: 'Non-smoker',
  marker: { color: '#4c78a8', size: 6 }
};
const traceYes = {
  x: """ + json.dumps(scatter_smoker_yes["x"]) + """,
  y: """ + json.dumps(scatter_smoker_yes["y"]) + """,
  text: """ + json.dumps(scatter_smoker_yes["text"]) + """,
  mode: 'markers',
  type: 'scatter',
  name: 'Smoker',
  marker: { color: '#f28c2e', size: 6 }
};
Plotly.newPlot('scatter', [traceNo, traceYes], {
  title: { text: 'Total Bill vs Tip (colored by smoker status)' },
  xaxis: { title: 'Total Bill ($)' },
  yaxis: { title: 'Tip ($)' },
  hovermode: 'closest'
});

// ---------- Bar: average tip % by day ----------
const barTrace = {
  x: """ + json.dumps(bar_x) + """,
  y: """ + json.dumps(bar_y) + """,
  type: 'bar',
  marker: { color: '#4c78a8' }
};
Plotly.newPlot('bar', [barTrace], {
  title: { text: 'Average Tip Percentage by Day of Week' },
  xaxis: { title: 'Day' },
  yaxis: { title: 'Tip (%)' }
});

// ---------- Box: tip distribution by gender ----------
const boxTraceMale = {
  y: """ + json.dumps(gender_male) + """,
  type: 'box',
  name: 'Male',
  marker: { color: '#4c78a8' }
};
const boxTraceFemale = {
  y: """ + json.dumps(gender_female) + """,
  type: 'box',
  name: 'Female',
  marker: { color: '#f28c2e' }
};
Plotly.newPlot('box', [boxTraceMale, boxTraceFemale], {
  title: { text: 'Tip Amount Distribution by Gender' },
  yaxis: { title: 'Tip ($)' }
});
</script>
</body>
</html>
"""

with open("dashboard.html", "w") as f:
    f.write(html)

print("✅ dashboard.html generated – open in browser.")
