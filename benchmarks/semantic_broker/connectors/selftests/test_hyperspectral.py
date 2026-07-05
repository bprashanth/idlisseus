#!/usr/bin/env python3
"""Ground-truth self-test for the `hyperspectral` connector (NOTES.md §3).

EMIT covers the EBTL area (29 scenes, verified 2026-07-04). For a covered vegetated
point the narrow-band indices must be valid — a broken wavelength->band mapping would
yield nulls/garbage. Tests coverage + plausible ranges, not exact values (EMIT is a
median over sparse acquisitions).
"""
import sys

sys.path.insert(0, "/opt/data")
from connectors.hyperspectral import indices  # noqa: E402

CHECKS = [
    ("ebtl_site", 12.735, 78.184,
     lambda r: r["coverage"] and r["ndvi_hyp"] is not None and 0.15 < r["ndvi_hyp"] < 0.9,
     "EBTL: covered and ndvi_hyp in (0.15,0.9)"),
    ("melagiri_forest", 12.60, 78.05,
     lambda r: r["coverage"] and r["rededge"] is not None and r["rededge"] > 0.05,
     "forest: covered and red-edge chlorophyll > 0.05"),
]


def main():
    pts = [{"id": c[0], "lat": c[1], "lon": c[2]} for c in CHECKS]
    got = indices(pts)
    ok = True
    for c, r in zip(CHECKS, got):
        passed = bool(c[3](r))
        ok = ok and passed
        print(f"[{'PASS' if passed else 'FAIL'}] {c[0]:16s} {c[4]:42s} "
              f"-> cov={r['coverage']} ndvi_hyp={r['ndvi_hyp']} rededge={r['rededge']}")
    print("SELFTEST:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
