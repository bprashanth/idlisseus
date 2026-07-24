#!/usr/bin/env python3
"""Ground-truth self-test for the `ecoregion` connector (NOTES.md §3).

Bet-money-on points in three distinct ecoregions (verified 2026-07-03):
  Anamalai      -> South Western Ghats montane rain forests
  Krishnagiri   -> South Deccan Plateau dry deciduous forests
  Sundarbans    -> Sundarbans mangroves
A broken spatial join would misname at least one.
"""
import sys

sys.path.insert(0, "/opt/data")
from connectors.ecoregion import at  # noqa: E402

FIXTURE = [
    {"id": "anamalai", "lat": 10.35, "lon": 76.93,
     "expected": "South Western Ghats montane rain forests"},
    {"id": "krishnagiri", "lat": 12.55, "lon": 78.20,
     "expected": "South Deccan Plateau dry deciduous forests"},
    {"id": "sundarbans", "lat": 21.95, "lon": 88.90,
     "expected": "Sundarbans mangroves"},
]


def main():
    pts = [{"id": p["id"], "lat": p["lat"], "lon": p["lon"]} for p in FIXTURE]
    got = at(pts)
    ok = True
    for exp, g in zip(FIXTURE, got):
        passed = g.get("ecoregion") == exp["expected"]
        ok = ok and passed
        print(f"[{'PASS' if passed else 'FAIL'}] {exp['id']:12s} "
              f"expected={exp['expected']!r} got={g.get('ecoregion')!r}")
    print("SELFTEST:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
