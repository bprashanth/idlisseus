"""pull_occurrence.py — build the EBTL SDM training set: GBIF + NCF camera-trap, pooled.

The EBTL corpus audit showed open *paper* repositories hold almost no georeferenced
dry-Deccan data. The data that DOES exist and is correctly placed is OCCURRENCE data:
GBIF (a firehose for elephant/gaur/chital/dhole/Lantana/Prosopis across the dry Deccan)
plus NCF camera-trap records. Occurrence data feeds the SDM/climate-suitability branch
(project a species' climatic niche into EBTL) — NOT the continuous-value RF branch.

This pools both sources over the dry-Deccan belt (the climate envelope that SPANS EBTL,
from moist-deciduous Bandipur/BRT to dry-thorn Krishnagiri) into one labelled table the
SDM can train on. Each row: lat, lon, species, label(guild), source.

  python3 ebtl/pull_occurrence.py
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "semantic_broker", "connectors"))
import occurrence as occ  # noqa: E402

# dry-Deccan belt: Bandipur/Mudumalai (W) -> BRT/MM Hills/Cauvery -> Hosur/Krishnagiri (E).
# Spans moist-deciduous -> dry-thorn, so the climate envelope covers EBTL (MESS-valid).
DRY_DECCAN = [76.0, 11.0, 79.5, 13.6]
INDEX = os.path.join(HERE, "..", "research", "paper_data_index.jsonl")
OUT = os.path.join(HERE, "occurrence_ebtl.csv")

# EBTL species of interest -> guild label the SDM predicts suitability for.
SPECIES = {
    "Elephas maximus": "elephant",
    "Bos gaurus": "gaur",
    "Axis axis": "chital",
    "Rusa unicolor": "sambar",
    "Muntiacus muntjak": "muntjac",
    "Cuon alpinus": "dhole",
    "Lantana camara": "invasive_lantana",
    "Prosopis juliflora": "invasive_prosopis",
}


def _in(bbox, lat, lon):
    w, s, e, n = bbox
    return w <= lon <= e and s <= lat <= n


def gbif_rows():
    rows = []
    for sp, label in SPECIES.items():
        try:
            pts = occ.search(sp, DRY_DECCAN, limit=1000)
        except Exception as ex:
            print(f"  ! GBIF {sp}: {str(ex)[:50]}"); continue
        pts = pts if isinstance(pts, list) else pts.get("points", [])
        for p in pts:
            if p.get("lat") is not None and p.get("lon") is not None:
                rows.append({"lat": round(p["lat"], 6), "lon": round(p["lon"], 6),
                             "species": sp, "label": label, "source": "gbif"})
        print(f"  gbif {sp:22s} {sum(1 for r in rows if r['species']==sp):4d}")
    return rows


def cameratrap_rows():
    """NCF camera-trap / paper occurrence points in the belt, matched to our species."""
    if not os.path.exists(INDEX):
        return []
    sci = {k.lower(): (k, v) for k, v in SPECIES.items()}
    rows = []
    for line in open(INDEX):
        r = json.loads(line)
        if r.get("value_type") != "species":
            continue
        val = str(r.get("value", "")).strip().lower()
        hit = sci.get(val)
        if hit and _in(DRY_DECCAN, r["lat"], r["lon"]):
            rows.append({"lat": r["lat"], "lon": r["lon"], "species": hit[0],
                         "label": hit[1], "source": "cameratrap"})
    return rows


def main():
    print("== GBIF occurrence (dry-Deccan belt) ==")
    g = gbif_rows()
    print("== NCF camera-trap occurrence ==")
    c = cameratrap_rows()
    rows = g + c
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["lat", "lon", "species", "label", "source"])
        w.writeheader(); w.writerows(rows)
    import collections
    by_label = collections.Counter(r["label"] for r in rows)
    by_src = collections.Counter(r["source"] for r in rows)
    print(f"\npooled {len(rows)} occurrence points -> {OUT}")
    print("  by source:", dict(by_src))
    print("  by guild :", dict(by_label))
    print("  (feeds predict.sdm_climate / presence as training; NOT continuous-value RF)")


if __name__ == "__main__":
    main()
