#!/usr/bin/env python3
"""Download tips data and build a self-contained dashboard.html."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DATA_URL = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv"
SCRIPT_DIR = Path(__file__).resolve().parent
CSV_PATH = SCRIPT_DIR / "tips.csv"
HTML_PATH = SCRIPT_DIR / "dashboard.html"

DAY_ORDER = ["Thur", "Fri", "Sat", "Sun"]
SMOKER_COLORS = {"Yes": "#e45756", "No": "#4c78a8"}
GENDER_COLORS = {"Female": "#f58518", "Male": "#54a24b"}


def download_dataset() -> pd.DataFrame:
    if not CSV_PATH.exists():
        urllib.request.urlretrieve(DATA_URL, CSV_PATH)
    return pd.read_csv(CSV_PATH)


def build_dashboard(df: pd.DataFrame) -> str:
    df = df.copy()
    df["tip_pct"] = (df["tip"] / df["total_bill"]) * 100

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Total Bill vs Tip (by Smoker Status)",
            "Average Tip Percentage by Day of Week",
            "Tip Amount Distribution by Gender",
        ),
        specs=[
            [{"type": "scatter"}, {"type": "bar"}],
            [{"type": "histogram", "colspan": 2}, None],
        ],
        vertical_spacing=0.12,
        horizontal_spacing=0.08,
    )

    for smoker in ["No", "Yes"]:
        subset = df[df["smoker"] == smoker]
        fig.add_trace(
            go.Scatter(
                x=subset["total_bill"],
                y=subset["tip"],
                mode="markers",
                name=f"Smoker: {smoker}",
                marker=dict(color=SMOKER_COLORS[smoker], size=8, opacity=0.75),
                legendgroup=smoker,
                showlegend=True,
            ),
            row=1,
            col=1,
        )

    avg_by_day = (
        df.groupby("day", observed=True)["tip_pct"]
        .mean()
        .reindex(DAY_ORDER)
        .reset_index()
    )
    fig.add_trace(
        go.Bar(
            x=avg_by_day["day"],
            y=avg_by_day["tip_pct"],
            marker_color="#72b7b2",
            name="Avg tip %",
            showlegend=False,
            hovertemplate="Day: %{x}<br>Avg tip: %{y:.1f}%<extra></extra>",
        ),
        row=1,
        col=2,
    )

    for sex in ["Female", "Male"]:
        subset = df[df["sex"] == sex]
        fig.add_trace(
            go.Histogram(
                x=subset["tip"],
                name=sex,
                marker_color=GENDER_COLORS[sex],
                opacity=0.65,
                nbinsx=15,
                legendgroup=sex,
                showlegend=True,
            ),
            row=2,
            col=1,
        )

    fig.update_xaxes(title_text="Total Bill ($)", row=1, col=1)
    fig.update_yaxes(title_text="Tip ($)", row=1, col=1)
    fig.update_xaxes(title_text="Day of Week", row=1, col=2)
    fig.update_yaxes(title_text="Average Tip (%)", row=1, col=2)
    fig.update_xaxes(title_text="Tip Amount ($)", row=2, col=1)
    fig.update_yaxes(title_text="Count", row=2, col=1)

    fig.update_layout(
        title=dict(
            text="Restaurant Tips Dashboard",
            x=0.5,
            xanchor="center",
            font=dict(size=22),
        ),
        barmode="overlay",
        height=900,
        width=1100,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.5, xanchor="center"),
        template="plotly_white",
        margin=dict(t=100, b=60, l=60, r=40),
    )

    plot_html = fig.to_html(full_html=False, include_plotlyjs="inline", div_id="dashboard-charts")

    summary = {
        "records": len(df),
        "avg_bill": round(df["total_bill"].mean(), 2),
        "avg_tip": round(df["tip"].mean(), 2),
        "avg_tip_pct": round(df["tip_pct"].mean(), 1),
    }

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Restaurant Tips Dashboard</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      margin: 0;
      padding: 24px;
      background: #f6f8fb;
      color: #1f2933;
    }}
    .container {{
      max-width: 1150px;
      margin: 0 auto;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 1.75rem;
    }}
    .subtitle {{
      margin: 0 0 20px;
      color: #52606d;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }}
    .card {{
      background: #fff;
      border-radius: 10px;
      padding: 14px 16px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
    }}
    .card .label {{
      font-size: 0.85rem;
      color: #616e7c;
    }}
    .card .value {{
      font-size: 1.4rem;
      font-weight: 600;
      margin-top: 4px;
    }}
    .chart-panel {{
      background: #fff;
      border-radius: 10px;
      padding: 8px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
    }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Restaurant Tips Dashboard</h1>
    <p class="subtitle">Summary of {summary["records"]} restaurant bills from the Seaborn tips dataset.</p>
    <div class="cards">
      <div class="card"><div class="label">Records</div><div class="value">{summary["records"]}</div></div>
      <div class="card"><div class="label">Avg Bill</div><div class="value">${summary["avg_bill"]}</div></div>
      <div class="card"><div class="label">Avg Tip</div><div class="value">${summary["avg_tip"]}</div></div>
      <div class="card"><div class="label">Avg Tip %</div><div class="value">{summary["avg_tip_pct"]}%</div></div>
    </div>
    <div class="chart-panel">
      {plot_html}
    </div>
  </div>
  <script id="embedded-data" type="application/json">{json.dumps(summary)}</script>
</body>
</html>
"""


def main() -> None:
    df = download_dataset()
    html = build_dashboard(df)
    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {HTML_PATH}")


if __name__ == "__main__":
    main()
