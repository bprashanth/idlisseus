#!/usr/bin/env python3
"""Ground-truth self-test for the `landcover` connector (NOTES.md §3).

The gate the whole loop hangs from: a gold answer may only be minted from a
connector that passes this. Fixture points are unambiguous and empirically
confirmed against ESA WorldCover v200 (2026-07-03):

  Coimbatore city centre       -> Built-up (50)
  Manamboli mature TR forest   -> Tree cover (10)
  Parambikulam reservoir       -> Permanent water bodies (80)

Run inside the hermes image (venv python has earthengine-api):
  python3 /opt/data/selftest/test_landcover.py
Exit 0 = all pass (connector trusted). Non-zero = REJECTED, do not mint gold.
"""
import sys

sys.path.insert(0, "/opt/data")
from connectors.landcover import classify  # noqa: E402

FIXTURE = [
    {"id": "coimbatore", "lat": 11.017, "lon": 76.958, "expected": "Built-up"},
    {"id": "manamboli", "lat": 10.358, "lon": 76.890, "expected": "Tree cover"},
    {"id": "parambikulam", "lat": 10.395, "lon": 76.795,
     "expected": "Permanent water bodies"},
]


def main():
    pts = [{"id": p["id"], "lat": p["lat"], "lon": p["lon"]} for p in FIXTURE]
    got = classify(pts)
    ok = True
    for exp, g in zip(FIXTURE, got):
        actual = g.get("landcover")
        passed = actual == exp["expected"]
        ok = ok and passed
        print(f"[{'PASS' if passed else 'FAIL'}] {exp['id']:14s} "
              f"expected={exp['expected']!r:26s} got={actual!r}")
    print("SELFTEST:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
