#!/usr/bin/env python3
"""goldmint — mint a gold answer by running a TESTED connector chain (NOTES.md §4).

Runs inside the hermes image (venv has ee). Produces points with occurrence.search,
annotates with the named connector, groups, and prints gold JSON + lineage. Gold is
only ever minted here (from gated connectors), never from the Solver's own output.

  python3 goldmint.py --species "Lantana camara" --bbox w,s,e,n --annotate landcover --group landcover
"""
import argparse
import json
import statistics
import sys

sys.path.insert(0, "/opt/data")
from connectors import occurrence, landcover, terrain, protected_areas  # noqa: E402


def mint(species, bbox, annotate, group, limit=300):
    pts = occurrence.search(species, bbox, limit=limit)
    n = len(pts)
    if n == 0:
        return {"n_points": 0, "group": group, "result": {},
                "note": "no occurrence points — question unanswerable in this AOI"}
    if annotate == "landcover":
        rows = landcover.classify(pts)
        counts = {}
        for r in rows:
            counts[r.get("landcover") or "unknown"] = counts.get(r.get("landcover") or "unknown", 0) + 1
        result = dict(sorted(counts.items(), key=lambda kv: -kv[1]))
    elif annotate == "terrain":
        elev = [r["elevation"] for r in terrain.at(pts) if r.get("elevation") is not None]
        result = {"min": min(elev), "median": round(statistics.median(elev), 1),
                  "max": max(elev), "n": len(elev)} if elev else {}
    elif annotate == "protected_areas":
        rows = protected_areas.contains(pts)
        inside = sum(1 for r in rows if r.get("in_pa"))
        result = {"inside": inside, "outside": n - inside,
                  "coverage_warning": "WDPA India coverage is patchy — in_pa=False is not "
                                      "proof of 'outside all PAs'"}
    else:
        return {"error": f"unknown annotate connector: {annotate}"}
    return {"n_points": n, "produce": f"occurrence.search('{species}')",
            "annotate": annotate, "group": group, "result": result}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--species", required=True)
    ap.add_argument("--bbox", required=True)
    ap.add_argument("--annotate", required=True)
    ap.add_argument("--group", required=True)
    ap.add_argument("--limit", type=int, default=300)
    a = ap.parse_args()
    bbox = [float(x) for x in a.bbox.split(",")]
    print(json.dumps(mint(a.species, bbox, a.annotate, a.group, a.limit), indent=2))
