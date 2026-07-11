#!/usr/bin/env python3
"""Ground-truth self-test for the `embedding` connector (NOTES.md §3).

AlphaEarth cosine similarity to an intact-forest reference (12.60, 78.05). Measured
2026-07-04: a forest-like site is very alike (~0.85), a city is unlike (~0.50).
Bounds are wide enough to be bet-money-on, tight enough that a wrong band/ref breaks them.
"""
import sys

sys.path.insert(0, "/opt/data")
from connectors.embedding import similarity  # noqa: E402

REF = [12.60, 78.05]   # intact dry-deciduous forest (Melagiri)
CHECKS = [
    ("ebtl_site", 12.735, 78.184, lambda s: s is not None and s > 0.70,
     "restoration site vs forest ref: cosine > 0.70"),
    ("coimbatore_city", 11.017, 76.958, lambda s: s is not None and s < 0.65,
     "city vs forest ref: cosine < 0.65"),
]


def main():
    pts = [{"id": c[0], "lat": c[1], "lon": c[2]} for c in CHECKS]
    got = similarity(pts, REF, year=2023)
    ok = True
    for c, r in zip(CHECKS, got):
        s = r.get("embed_sim")
        passed = bool(c[3](s))
        ok = ok and passed
        print(f"[{'PASS' if passed else 'FAIL'}] {c[0]:18s} {c[4]:44s} -> embed_sim={s}")
    print("SELFTEST:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
