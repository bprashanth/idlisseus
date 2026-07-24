#!/usr/bin/env python3
"""Ground-truth self-test for the `greenness` connector (NOTES.md §3).

NDVI is fuzzier than a class legend, so this tests direction/magnitude at
controlled points rather than an exact value (§3). Bounds are empirically
anchored (MOD13Q1, 2019-2024, measured 2026-07-03) and chosen wide enough to be
bet-money-on yet tight enough to catch a broken band / missing 0.0001 scale
factor (an unscaled break yields values in the thousands and blows the ceilings):

  Manamboli mature TR forest -> ndvi_end high (0.55-0.95) AND trend flat  (stable canopy)
  Coimbatore city centre     -> ndvi_end low  (0.15-0.45)                 (built-up)
  Parambikulam reservoir     -> ndvi_end < 0.30                           (water)

Exit 0 = all pass (connector trusted). Non-zero = REJECTED, do not mint gold.
"""
import sys

sys.path.insert(0, "/opt/data")
from connectors.greenness import trend  # noqa: E402

# each check: (id, lat, lon, predicate(row)->bool, human description)
CHECKS = [
    ("manamboli_forest", 10.358, 76.890,
     lambda r: r["ndvi_end"] is not None and 0.55 < r["ndvi_end"] < 0.95
               and r["trend_class"] == "flat",
     "intact forest: ndvi_end in (0.55,0.95) and trend flat"),
    ("coimbatore_city", 11.017, 76.958,
     lambda r: r["ndvi_end"] is not None and 0.15 < r["ndvi_end"] < 0.45,
     "city: ndvi_end in (0.15,0.45)"),
    ("parambikulam_water", 10.395, 76.795,
     lambda r: r["ndvi_end"] is not None and r["ndvi_end"] < 0.30,
     "water: ndvi_end < 0.30"),
]


def main():
    pts = [{"id": c[0], "lat": c[1], "lon": c[2]} for c in CHECKS]
    got = trend(pts, years="2019-2024")
    ok = True
    for c, r in zip(CHECKS, got):
        passed = bool(c[3](r))
        ok = ok and passed
        print(f"[{'PASS' if passed else 'FAIL'}] {c[0]:20s} {c[4]:48s} "
              f"-> ndvi_end={r['ndvi_end']} trend={r['trend_class']} slope={r['ndvi_slope']}")
    print("SELFTEST:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
