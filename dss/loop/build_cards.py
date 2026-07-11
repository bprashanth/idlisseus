"""Build enriched data cards over the WIDE corpus (research/paper_catalog.jsonl, 140 studies).

A card = per study: title + ALL column names across its files + codebook/README text
(which holds the column DEFINITIONS that decode cryptic names, e.g. densiometer=canopy,
slopeSRTM30=slope) + extracted value_types + georef status. This is the pre-computed
content index that makes BURIED data findable: a wildfire study's 'prosopis' column, a
bird study's 'densiometer' canopy reading, a frog study's 'T_euphlyctis' abundance.

v-1 (17 studies) proved cards are needed. This builds them at 8x scale so we can measure
whether retrieval (keyword / embeddings / LLM-over-cards) still holds up at 140 cards.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))               # dss/loop
CORPUS = os.path.join(HERE, "..", "corpus")                     # dss/corpus
CATALOG = os.path.join(CORPUS, "paper_catalog.jsonl")          # card source material (from crawl.py)
CARDS = os.path.join(CORPUS, "cards.jsonl")                    # what discovery.py embeds/searches

# columns that are parsing noise (a whole row swallowed into one "column", or blank)
_NOISE = re.compile(r"^(col\d+|unnamed|nan|none|)$", re.I)


def _clean_cols(columns_by_file):
    seen, out = set(), []
    for cols in columns_by_file.values():
        for c in cols:
            c = str(c).strip()
            if not c or len(c) > 60 or _NOISE.match(c):
                continue
            k = c.lower()
            if k not in seen:
                seen.add(k)
                out.append(c)
    return out


def build():
    rows = [json.loads(l) for l in open(CATALOG)]
    cards = []
    for r in rows:
        cols = _clean_cols(r.get("columns", {}))
        codebook = (r.get("codebook") or "").strip()
        # content = what retrieval matches against. Title + columns + codebook definitions.
        content = " ".join([r["title"] or ""] + cols + [codebook]).lower()
        cards.append({
            "doi": r.get("doi"), "title": r.get("title"), "hop": r.get("hop"),
            "columns": cols[:60], "n_columns": len(cols),
            "has_codebook": bool(codebook), "codebook": codebook[:4000],
            "value_type": r.get("value_type"), "n_points": r.get("n_points", 0),
            "strategy": r.get("strategy"), "content": content,
        })
    json.dump(cards, open(CARDS, "w"))
    return cards


if __name__ == "__main__":
    cards = build()
    n_cb = sum(c["has_codebook"] for c in cards)
    n_geo = sum(1 for c in cards if c["n_points"])
    tot_cols = sum(c["n_columns"] for c in cards)
    print(f"built {len(cards)} cards -> {CARDS}")
    print(f"  {n_cb} with codebook, {n_geo} georeferenced, {tot_cols} clean columns")
    print(f"  median cols/card = {sorted(c['n_columns'] for c in cards)[len(cards)//2]}")
    print(f"  biggest cards: " + ", ".join(
        f"{c['n_columns']}" for c in sorted(cards, key=lambda x: -x['n_columns'])[:5]))
