#!/usr/bin/env python3
"""Replay a ledger gold entry (NOTES.md §7): re-run the tested connector chain and
confirm it reproduces the stored gold. This is what makes a ledger entry a
*re-runnable* benchmark record rather than a one-off number.

Run inside the hermes image (venv python has ee):
  python3 /opt/data/selftest/replay.py \
      /opt/data/selftest/gold_greenness.json /opt/data/query_data/restoration_sites.csv
Exit 0 = reproduced; non-zero = drift.
"""
import csv
import json
import sys

sys.path.insert(0, "/opt/data")
from connectors.greenness import trend  # noqa: E402


def main():
    gold = json.load(open(sys.argv[1]))
    pts = []
    with open(sys.argv[2], newline="") as f:
        for row in csv.DictReader(f):
            low = {k.strip().lower(): v for k, v in row.items() if k}
            pts.append({"id": low.get("id") or low.get("site") or low.get("name"),
                        "lat": float(low["lat"]), "lon": float(low["lon"])})
    got = trend(pts, years="2019-2024")
    counts = {}
    for r in got:
        counts[r["trend_class"]] = counts.get(r["trend_class"], 0) + 1
    exp = gold["class_counts"]
    ok = counts == exp
    print(f"replayed class_counts={counts}")
    print(f"gold     class_counts={exp}")
    print("REPLAY:", "REPRODUCED" if ok else "DRIFT")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
