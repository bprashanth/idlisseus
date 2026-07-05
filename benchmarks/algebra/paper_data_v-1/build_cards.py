"""Build data cards (content index) for the corpus and re-test the buried queries.

A data card = per study: title + ALL column names across its files + codebook excerpt +
the extracted value_types/species. Retrieval then matches a concept against the CARD
(content), not just the title — so buried data (a logging study's 'slope', a bird study's
'canopy') becomes findable. This is the cheap, pre-computed version of inspect-everything.
"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "semantic_broker", "connectors"))
import paper_data as pd  # noqa: E402

INDEX = os.path.join(HERE, "..", "research", "paper_data_index.jsonl")
CARDS = os.path.join(HERE, "cards.jsonl")


def build():
    rows = [json.loads(l) for l in open(INDEX)]
    vts = collections.defaultdict(set); sp = collections.defaultdict(set)
    title = {}
    for r in rows:
        title[r["doi"]] = r["dataset"]; vts[r["doi"]].add(r["value_type"])
        if r["value_type"] == "species" and r["value"]:
            sp[r["doi"]].add(str(r["value"]))
    # inspect each dataset for ALL columns + codebook
    ds_by_title = {d["title"]: d for d in pd.find(community="ncf", size=25)}
    cards = []
    for doi, t in title.items():
        ds = next((d for d in ds_by_title.values() if d["title"] == t), None)
        cols, codebook = [], ""
        if ds:
            mat = pd.inspect(ds)
            codebook = mat["codebook"][:1500]
            for f in mat["files"]:
                if f["sample"]:
                    cols += [c.strip() for c in re.split(r"[,\t]", f["sample"][0])]
        content = " ".join([t] + cols + [codebook] + list(vts[doi]) + list(sp[doi])).lower()
        cards.append({"doi": doi, "title": t, "columns": sorted(set(cols))[:40],
                      "value_types": sorted(vts[doi]), "n_species": len(sp[doi]),
                      "content": content})
    json.dump(cards, open(CARDS, "w"), indent=1)
    return cards


def card_search(cards, concept):
    """Match a concept against card CONTENT (columns + codebook + values), not just title."""
    toks = [w for w in re.findall(r"[a-z]{3,}", concept.lower())]
    hits = []
    for c in cards:
        if any(t in c["content"] for t in toks):
            hits.append(c["title"])
    return hits


BURIED = [("terrain slope", "Varying impacts of logging"),
          ("canopy cover", "Birds and Vegetation of Shade Coffee"),
          ("leaf litter", "Birds and Vegetation of Shade Coffee"),
          ("frog amphibian abundance", "Abiotic and biotic drivers on tadpoles")]


if __name__ == "__main__":
    cards = build()
    print(f"built {len(cards)} data cards -> {CARDS}\n")
    print("=== re-test the BURIED queries against the CARD (content) index ===")
    recovered = 0
    for concept, tgt in BURIED:
        hits = card_search(cards, concept)
        found = any(tgt.lower() in h.lower() for h in hits)
        recovered += found
        print(f"[{'CARD-FOUND' if found else 'still MISS'}] {concept!r} -> target study surfaced: {found}")
        if found:
            print(f"      (matched via columns/codebook, e.g. {[c['columns'] for c in cards if c['title']==next(h for h in hits if tgt.lower() in h.lower())][0][:6]})")
    print(f"\nrecovered {recovered}/{len(BURIED)} buried cases with data cards "
          f"(metadata search had missed 3/4).")
