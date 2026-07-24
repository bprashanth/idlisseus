"""ask.py — answer an open user question from the indexed knowledge base + a live
data reading, always pointing at where the data came from. Gives *some* grounded
answer where data exists, and says plainly where it doesn't.

  python3 research/ask.py --aoi aois/elephants_by_the_lake.json "is a new invasive showing up?"
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kb, measure  # noqa: E402

# genus names worth a live occurrence check
_KNOWN_TAXA = {
    "lantana": "Lantana camara", "prosopis": "Prosopis juliflora",
    "parthenium": "Parthenium hysterophorus", "chromolaena": "Chromolaena odorata",
    "elephant": "Elephas maximus", "sloth bear": "Melursus ursinus",
    "snake eagle": "Circaetus gallicus", "junglefowl": "Gallus sonneratii",
}


def ask(question, aoi):
    ql = question.lower()
    print(f"Q: {question}\n" + "-" * 70)

    # 1) live occurrence-over-time reading if the question names/implies a taxon
    live = None
    taxon = next((sci for key, sci in _KNOWN_TAXA.items() if key in ql), None)
    if taxon is None and any(w in ql for w in ("invasive", "showing up", "appearing", "spreading", "new")):
        taxon = "Lantana camara"   # default invasive probe for the AOI
    if taxon:
        r = measure.gbif_by_year(taxon, [float(x) for x in aoi["bbox"]])
        if r.get("measured"):
            live = r
            print(f"LIVE ({taxon}, {r['source']}): {r['total_records']} records, "
                  f"first seen {r['first_year']}, {r['recent_2020plus']} since 2020 "
                  f"vs {r['prior_2014_2019']} in 2014-19 -> **{r['trend']}**")
            print(f"     source: {r['provenance']['source_url'][:80]}…")
        else:
            print(f"LIVE ({taxon}): {r.get('note') or r.get('reason')} "
                  f"(total {r.get('total_records','?')} records)")

    # 1b) modelled corroboration (predict RF on embeddings + EMIT) for this taxon
    if taxon:
        for r in kb.load():
            if r.get("theme") == "corroboration" and taxon.lower() in json.dumps(r).lower():
                res = r["result"]
                print(f"MODELLED ({r['indicator']['indicator']}): present_fraction="
                      f"{res.get('present_fraction')} (RF acc {res.get('model_accuracy')}, "
                      f"{res.get('source')}) — corroborative, not observed")
                break

    # 2) indexed knowledge from mined papers + prior readings
    hits = kb.retrieve(question, k=5)
    if hits:
        print("\nFROM THE INDEX (mined papers + prior readings):")
        for h in hits:
            ind = h["indicator"]; res = h["result"]; pap = h.get("paper", {})
            if h["status"] == "measured":
                val = {k: v for k, v in res.items()
                       if k in ("trend", "recent_2020plus", "ndvi_trend", "n_matched",
                                "total_records", "landcover", "fire_count_5km_5yr")}
                print(f"  • {ind['indicator']}: {val}")
                print(f"    source: {res.get('source','connector')} | paper: {(pap.get('title') or '')[:55]} ({pap.get('doi')})")
            else:
                print(f"  • {ind['indicator']}: DATA GAP — {res.get('reason','')}")
                if res.get("suggestion"):
                    print(f"    → {res['suggestion']}")
    else:
        print("\nFROM THE INDEX: nothing indexed yet for this question "
              "(run research/loop.py on more themes).")

    # 3) honest verdict
    print("\nVERDICT:")
    if live and live.get("measured"):
        print(f"  Yes — there is real signal ({live['trend']}), from {live['source']}. "
              "Coverage is limited to georeferenced records; corroborate with a field check.")
    elif hits:
        print("  Partial — see indexed evidence above; note the data gaps and their sources.")
    else:
        print("  No indexed data yet. This is a collect-it / mine-more case.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--aoi", required=True)
    ap.add_argument("question", nargs="+")
    a = ap.parse_args()
    ask(" ".join(a.question), json.load(open(a.aoi)))
