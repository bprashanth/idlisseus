#!/usr/bin/env python3
"""discovery_bench — does SEMANTIC retrieval (embeddings over cards) beat KEYWORD over the same corpus?

The hypothesis the wire-up rests on: a lay/paraphrased query ("invasive weed spreading in coffee",
"animals killed on roads") should reach a dataset whose TITLE uses different words ("Brewing trouble:
coffee invasion", "wildlife roadkills") — the semantic map that keyword search misses. We hold the CORPUS
constant (the same 169 cards) and vary only the retriever, so any gap is the embeddings lever, not the
cards. Metrics: recall@5 and MRR over a hand-labelled query→DOI set of deliberately paraphrased queries.

Run INSIDE the hermes container (needs the fastembed venv + the /opt/data/corpus mount):
  docker cp bench.py hermes-live:/opt/data/work/bench.py
  docker exec hermes-live /opt/data/work/venv/bin/python3 /opt/data/work/bench.py
"""
import json
import re
import sys

sys.path.insert(0, "/opt/data/connectors")
import discovery  # noqa: E402

CORPUS = "/opt/data/corpus/cards.jsonl"

# query -> substring(s) that identify the ground-truth relevant card by title. Queries are deliberately
# LAY / paraphrased so the target title uses DIFFERENT vocabulary (the semantic test). Multiple substrings
# = any of these titles counts as relevant.
GOLD = [
    ("what a leopard eats in tea estates",        ["leopard diet"]),
    ("weed taking over coffee plantations",       ["coffee invasion", "invasive weed"]),
    ("animals run over on roads",                 ["roadkill"]),
    ("frogs breeding in rock pools",              ["rock pools", "rock outcrop amphib"]),
    ("bee numbers on tribal coffee farms",        ["pollinator abundance"]),
    ("birds coming back after replanting forest", ["recovery of tropical rainforest birds"]),
    ("carbon locked up in repeatedly logged forest", ["logging frequency", "carbon storage in rain"]),
    ("spread of an introduced mynah bird",        ["invasive common myna"]),
    ("how tree seeds get eaten by small rodents", ["seed predation", "small mammals reduce"]),
    ("fruit-eating birds and how much forest is left", ["frugivory", "fruit crop size"]),
    ("soil health during forest replanting",      ["soil dynamics in forest restoration", "soil"]),
    ("large mammals seen around the anamalai tiger reserve", ["mammal occurrence"]),
]


def _cards():
    return json.load(open(CORPUS))


def keyword_search(query, cards, k=5):
    """BM25-lite: rank cards by count of query terms occurring in the card's searchable content."""
    terms = [t for t in re.findall(r"[a-z]+", query.lower()) if len(t) > 2]
    scored = []
    for c in cards:
        text = (c.get("content") or c.get("title") or "").lower()
        score = sum(text.count(t) for t in terms)
        scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    return [c for s, c in scored[:k] if s > 0]


def hit_rank(results, gold_subs):
    for i, c in enumerate(results):
        title = (c.get("title") or "").lower()
        if any(g.lower() in title for g in gold_subs):
            return i + 1
    return 0


def run(k=5):
    cards = _cards()
    rows = []
    kw_recall = emb_recall = kw_mrr = emb_mrr = 0.0
    for q, gold in GOLD:
        kw = keyword_search(q, cards, k)
        emb = discovery.search(q, k=k)["results"]
        kr = hit_rank(kw, gold)
        er = hit_rank(emb, gold)
        kw_recall += (kr > 0)
        emb_recall += (er > 0)
        kw_mrr += (1.0 / kr) if kr else 0.0
        emb_mrr += (1.0 / er) if er else 0.0
        rows.append((q, kr, er, (emb[0]["title"][:52] if emb else "-")))
    n = len(GOLD)
    print(f"\n{'query':44s} kw@rank emb@rank  emb top-1")
    print("-" * 108)
    for q, kr, er, top in rows:
        print(f"{q[:44]:44s} {str(kr or '-'):>6s} {str(er or '-'):>8s}  {top}")
    print("-" * 108)
    print(f"{'RECALL@'+str(k):44s} {kw_recall/n:6.2f} {emb_recall/n:8.2f}")
    print(f"{'MRR':44s} {kw_mrr/n:6.2f} {emb_mrr/n:8.2f}")
    print(f"\nn={n} paraphrased queries · corpus={len(cards)} cards · retriever is the only variable")


if __name__ == "__main__":
    run()
