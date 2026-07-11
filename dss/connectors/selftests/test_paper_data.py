#!/usr/bin/env python3
"""Ground-truth self-test for the `paper_data` connector (NOTES.md §3).

Bet-money-on: NCF's Zenodo mammal-occurrence datasets contain many gaur (Bos gaurus)
records in the Anamalai AOI. A working find+ingest+search returns them, in-AOI, with
the value correctly extracted. Verifies coord/species detection end-to-end on live data.
"""
import sys

sys.path.insert(0, "/opt/data/connectors")
sys.path.insert(0, __file__.rsplit("/", 3)[0] + "/semantic_broker/connectors")
import paper_data as pd  # noqa: E402

AOI = [76.3, 10.2, 77.2, 11.7]   # Anamalai-Nilgiris


def main():
    res = pd.search("gaur", AOI, community="ncf", query="mammal occurrence", max_datasets=4)
    n_in = res["counts"]["in_aoi"]
    n_ds = res["counts"]["datasets"]
    ok_vals = all("gaur" in str(p.get("value", "")).lower() for p in res["in_aoi"][:15])
    checks = [
        (n_ds >= 2, f"found >=2 NCF datasets (got {n_ds})"),
        (n_in >= 50, f"gaur points in AOI >=50 (got {n_in})"),
        (ok_vals, "extracted values are gaur"),
    ]
    ok = all(c for c, _ in checks)
    for c, m in checks:
        print(f"[{'PASS' if c else 'FAIL'}] {m}")
    print("SELFTEST:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
