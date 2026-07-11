#!/usr/bin/env python3
"""discovery — SEMANTIC retrieval over the ingested paper/dataset CORPUS (cards + embeddings).

Why: `paper_data.find`/`litscout` do keyword/API search over titles — they miss buried data (a `lantana`
column inside a dataset titled "canopy structure") and fumble on over-scoped queries. This connector
retrieves over **content cards** (title + ALL column names + codebook definitions) with **bge-small
embeddings**, so a lay/semantic query ("invasives near my seedlings", "what eats snakes") reaches the right
dataset — including its buried columns. The big lever is the CARDS (codebook-in-card); embeddings add
semantic reach + scale-robustness. Complements live API discovery, doesn't replace it.

  search(query, k=5, points_only=False) -> ranked cards {doi, title, n_points, matched_columns, score}
  CLI: discovery.py search --query "lantana invasive dry forest" [--k 5] [--points-only]
Corpus: /opt/data/corpus/cards.jsonl (mounted from dss/corpus). Embeddings cached to /opt/data/work/discovery.
Bridge: feed a returned `doi` to `paper_data.extract --url <doi>` to pull the presence POINTS inside.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import sys

# self-heal: fastembed + numpy live in the PERSISTENT work venv (under the /opt/data mount, so it survives
# container restarts — unlike the image venv). The agent's default python3 lacks them.
_VENV = "/opt/data/work/venv/bin/python3"
if (importlib.util.find_spec("fastembed") is None and os.path.exists(_VENV)
        and not os.environ.get("_DISC_REEXEC")):
    os.environ["_DISC_REEXEC"] = "1"
    os.execv(_VENV, [_VENV] + sys.argv)

import numpy as np                       # noqa: E402
from fastembed import TextEmbedding      # noqa: E402

CORPUS = os.environ.get("CORPUS_CARDS", "/opt/data/corpus/cards.jsonl")
CACHE_DIR = os.environ.get("DISCOVERY_CACHE", "/opt/data/work/discovery")
_MODEL = None


def _model():
    global _MODEL
    if _MODEL is None:
        _MODEL = TextEmbedding()          # default = BAAI/bge-small-en-v1.5 (ONNX, ~130MB, no torch)
    return _MODEL


def _cards():
    return json.load(open(CORPUS))


def _corpus_emb(cards):
    os.makedirs(CACHE_DIR, exist_ok=True)
    h = hashlib.sha1((str(len(cards)) + (cards[0].get("doi") or "")).encode()).hexdigest()[:10]
    p = os.path.join(CACHE_DIR, f"emb_{h}.npy")
    if os.path.exists(p):
        return np.load(p)
    texts = [(c.get("content") or c.get("title") or "")[:2000] for c in cards]
    emb = np.asarray(list(_model().embed(texts)), dtype=np.float32)
    emb /= (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9)
    np.save(p, emb)
    return emb


def search(query, k=5, points_only=False):
    cards = _cards()
    emb = _corpus_emb(cards)
    q = np.asarray(list(_model().embed([query]))[0], dtype=np.float32)
    q /= (np.linalg.norm(q) + 1e-9)
    sims = emb @ q
    idx = [i for i in range(len(cards)) if (not points_only) or (cards[i].get("n_points") or 0) > 0]
    ranked = sorted(idx, key=lambda i: -sims[i])[:k]
    return {"query": query, "k": k, "corpus": len(cards),
            "results": [{"doi": cards[i].get("doi"), "title": cards[i].get("title"),
                         "n_points": cards[i].get("n_points"), "has_codebook": cards[i].get("has_codebook"),
                         "score": round(float(sims[i]), 3),
                         "matched_columns": (cards[i].get("columns") or [])[:8]} for i in ranked]}


def describe():
    return {
        "connector": "discovery",
        "purpose": "Semantic retrieval over the ingested paper/dataset corpus (content cards + bge-small).",
        "produces": "ranked cards with DOI + n_points + matched columns — finds BURIED data keyword search misses.",
        "functions": ["search(query, k=5, points_only=False) -> ranked cards {doi,title,n_points,matched_columns,score}"],
        "use": "For a literature / dataset / 'what data exists on X' question, run this FIRST (semantic; one "
               "call, no keyword fumbling). `--points-only` keeps datasets with extractable points. Then feed "
               "a `doi` to `paper_data.extract --url <doi>` for the points inside. Complements litscout (live "
               "OpenAlex discovery of NEW papers) — discovery searches the INGESTED corpus.",
        "gotcha": "Corpus = /opt/data/corpus/cards.jsonl (256 cards). First run embeds the corpus (~cached to "
                  "/opt/data/work/discovery). bge-small via fastembed (self-heals to the venv). Semantic, not "
                  "keyword — good for lay/paraphrased queries.",
        "example": "python /opt/data/connectors/discovery.py search --query \"lantana invasive spread dry deciduous\" --points-only",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="discovery")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("search"); s.add_argument("--query", required=True)
    s.add_argument("--k", type=int, default=5); s.add_argument("--points-only", action="store_true")
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    print(json.dumps(search(args.query, args.k, args.points_only), indent=2))


if __name__ == "__main__":
    _main()
