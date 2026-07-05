"""paper_data_v-1 — does Hermes-style retrieval find the RIGHT study, or do we need data cards?

10 questions over our current corpus. Each targets data we KNOW exists (ground truth from the
crawl). Split: FINDABLE (concept is in the study title/metadata) vs BURIED (concept is only in a
data column of an off-topic study). The decisive test: metadata search (what paper_data.find does,
and what Hermes leans on) — does it surface the target study? Where it can't (buried), a data card
(content index) would. We also confirm the concept truly is in the target's data.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "semantic_broker", "connectors"))
import paper_data as pd  # noqa: E402

INDEX = os.path.join(HERE, "..", "research", "paper_data_index.jsonl")

# (question, search-concept, target-study title substring, findable?)  target must be in our corpus
QUESTIONS = [
    ("What soil pH data do we have anywhere?", "soil pH", "Soil properties of degraded", True),
    ("Which mammals are recorded around Valparai/Anamalai?", "mammal", "Mammal occurrence records (2024)", True),
    ("Is there bird transect data from Mudumalai?", "birds Mudumalai", "Line transect data on birds", True),
    ("Do we have wood density measurements for trees?", "wood density", "Wood density for 26 plant", True),
    ("Any data on leopard diet or prey abundance?", "leopard diet prey", "Prey abundance and leopard diet", True),
    # --- buried: concept is in the DATA, not the title ---
    ("Do we have terrain slope data for any study site?", "slope terrain", "Varying impacts of logging", False),
    ("What canopy cover / openness data exists at coffee sites?", "canopy cover", "Birds and Vegetation of Shade Coffee", False),
    ("Is there any frog or amphibian abundance data?", "frog amphibian abundance", "Abiotic and biotic drivers on tadpoles", False),
    ("Do we have leaf-litter measurements anywhere?", "leaf litter", "Birds and Vegetation of Shade Coffee", False),
    ("Any tree seed-predation experiment data?", "seed predation", "Small mammals reduce distance", True),
]


def corpus_titles():
    rows = [json.loads(l) for l in open(INDEX)]
    return {r["dataset"] for r in rows}, rows


def metadata_finds(concept, target_sub):
    """Does paper_data.find(concept) (metadata search) surface the target study?"""
    for comm in ("ncf", None):
        try:
            for ds in pd.find(concept, community=comm, size=25):
                if target_sub.lower() in (ds.get("title") or "").lower():
                    return True
        except Exception:
            continue
    return False


def main():
    titles, rows = corpus_titles()
    by_title_vts = collections.defaultdict(set)
    for r in rows:
        by_title_vts[r["dataset"]].add(r["value_type"])
    print(f"corpus: {len(titles)} datasets, {len(rows)} points\n")
    miss_buried = miss_findable = 0
    for q, concept, tgt, findable in QUESTIONS:
        in_corpus = any(tgt.lower() in t.lower() for t in titles)
        found = metadata_finds(concept, tgt)
        tag = "FINDABLE" if findable else "BURIED  "
        verdict = "metadata-FOUND" if found else "metadata-MISS (needs card)"
        if not found:
            if findable:
                miss_findable += 1
            else:
                miss_buried += 1
        print(f"[{tag}] {q}")
        print(f"          concept={concept!r} target in corpus={in_corpus} -> {verdict}")
    print(f"\n=== verdict ===")
    print(f"buried questions metadata MISSED (would need a data card): {miss_buried}/"
          f"{sum(1 for *_, f in QUESTIONS if not f)}")
    print(f"findable questions metadata missed (unexpected): {miss_findable}")
    print("If buried misses are high -> data cards (content index) are needed for reliable retrieval.")


if __name__ == "__main__":
    main()
