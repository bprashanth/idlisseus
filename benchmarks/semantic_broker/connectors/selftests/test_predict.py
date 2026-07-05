#!/usr/bin/env python3
"""Ground-truth self-test for the `predict` connector (NOTES.md §3).

ML gate: with adequate, clean ground truth the RF must (a) reach a real held-out
accuracy and (b) classify obvious held-out points correctly. Forest vs built-up is
very separable in AlphaEarth embedding space, so a competent model clears this
easily; a broken pipeline (no features / bad training) won't.
"""
import sys

sys.path.insert(0, "/opt/data")
from connectors.predict import transfer  # noqa: E402

# 10 known forests + 10 known cities across S. India
TRAIN = [(10.358, 76.890, "forest"), (12.60, 78.05, "forest"), (11.40, 76.70, "forest"),
         (11.10, 76.45, "forest"), (10.30, 76.90, "forest"), (11.70, 76.60, "forest"),
         (12.00, 76.10, "forest"), (11.90, 77.15, "forest"), (11.60, 76.50, "forest"),
         (8.60, 77.30, "forest"),
         (11.017, 76.958, "city"), (13.08, 80.27, "city"), (12.97, 77.59, "city"),
         (9.925, 78.12, "city"), (11.66, 78.15, "city"), (10.79, 78.70, "city"),
         (12.30, 76.65, "city"), (11.34, 77.72, "city"), (11.11, 77.34, "city"),
         (12.92, 79.13, "city")]
TARGETS = [("held_forest", 10.32, 76.88, "forest"), ("held_city", 13.34, 77.10, "city")]  # Kolar


def main():
    train = [{"lat": la, "lon": lo, "label": lb} for la, lo, lb in TRAIN]
    tgt = [{"id": t[0], "lat": t[1], "lon": t[2]} for t in TARGETS]
    r = transfer(train, tgt, year=2023, trees=150)
    acc = r.get("test_accuracy")
    preds = {p["id"]: p["predicted_label"] for p in r["predictions"]}
    ok_acc = acc is not None and acc >= 0.70
    ok_pred = all(preds.get(t[0]) == t[3] for t in TARGETS)
    print(f"[{'PASS' if ok_acc else 'FAIL'}] test_accuracy={acc} (>=0.70)")
    for t in TARGETS:
        p = preds.get(t[0]); ok = p == t[3]
        print(f"[{'PASS' if ok else 'FAIL'}] {t[0]:12s} predicted={p} expected={t[3]}")
    ok = ok_acc and ok_pred
    print("SELFTEST:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
