#!/usr/bin/env python3
"""litscout — literature discovery via the AUTHOR CO-AUTHORSHIP GRAPH + topic (OpenAlex, free).

The researcher-beating move: don't just keyword-search titles — walk the people. From a topic or a seed
author, find the tight cluster of authors who actually work on it, then pull THEIR works and especially
their DATASETS (OpenAlex `type:dataset`). Chain: author -> co-authors -> (topic-constrained) -> works ->
related datasets -> [bridge to paper_data.extract for the presence POINTS inside them].

Why this beats a plain lit review: a manual search finds the famous paper; the co-author graph surfaces
the same lab's *other* papers and their archived datasets (Zenodo/Dryad DOIs) that hold the actual points.

  works(query, kind=None, india=False)      # papers or datasets on a topic (kind='dataset'|'article')
  authors(query)                            # the co-authorship cluster for a topic (seed authors)
  expand(author, topic)                     # author -> co-authors -> their topic works + datasets
Stdlib only (urllib). Bridges to `paper_data` for point extraction from the dataset DOIs it finds.

  CLI: litscout.py works --query "Uropeltis Eastern Ghats" --kind dataset --india
       litscout.py authors --query "shieldtail snake phylogeny India"
       litscout.py expand --author "David J. Gower" --topic "Uropeltidae India"
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

MAILTO = "prashanthseven@gmail.com"          # OpenAlex "polite pool" (faster, no key needed)
BASE = "https://api.openalex.org"
CACHE = os.environ.get("LITSCOUT_CACHE", "/opt/data/work/litscout")


def _get(path, **params):
    params["mailto"] = MAILTO
    url = f"{BASE}/{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "idlisseus-litscout/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _work(w):
    auth = [a["author"]["display_name"] for a in (w.get("authorships") or [])][:8]
    topics = [t["display_name"] for t in (w.get("topics") or w.get("concepts") or [])][:3]
    loc = (w.get("primary_location") or {}).get("source") or {}
    return {"title": w.get("display_name"), "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
            "year": w.get("publication_year"), "type": w.get("type"), "oa": (w.get("open_access") or {}).get("is_oa"),
            "authors": auth, "topics": topics, "host": loc.get("display_name"),
            "id": (w.get("id") or "").replace("https://openalex.org/", "")}


def works(query, kind=None, india=False, limit=25):
    """OpenAlex works on a topic. kind='dataset' finds ARCHIVED DATASETS (where the points live)."""
    filt = []
    if kind == "dataset":
        filt.append("type:dataset")
    elif kind == "article":
        filt.append("type:article")
    if india:                                    # authored from an Indian institution
        filt.append("authorships.institutions.country_code:IN")
    p = {"search": query, "per_page": min(limit, 50), "sort": "relevance_score:desc"}
    if filt:
        p["filter"] = ",".join(filt)
    try:
        d = _get("works", **p)
    except Exception as e:
        return {"query": query, "error": str(e)[:80], "results": []}
    return {"query": query, "kind": kind or "any", "india": india, "count": d["meta"]["count"],
            "results": [_work(w) for w in d.get("results", [])]}


def authors(query, limit=12):
    """The co-authorship cluster for a topic: authors ranked by how often they appear on its works.
    These are the seeds to `expand` — the people whose labs archive the datasets."""
    d = works(query, limit=50)
    tally = {}
    for w in d["results"]:
        for a in w["authors"]:
            tally.setdefault(a, {"name": a, "papers": 0})
            tally[a]["papers"] += 1
    ranked = sorted(tally.values(), key=lambda x: -x["papers"])[:limit]
    return {"query": query, "topic_works": len(d["results"]), "authors": ranked}


def _resolve_author(name):
    try:
        d = _get("authors", search=name, per_page=1)
        r = d.get("results") or []
        return r[0] if r else None
    except Exception:
        return None


def expand(author, topic, limit=25):
    """author -> co-authors (from their topic works) -> the co-authors' works + DATASETS on the topic.
    The author->co-author->topic->datasets chain the researcher workflow wants."""
    a = _resolve_author(author)
    if not a:
        return {"author": author, "error": "author not found on OpenAlex", "coauthors": [], "datasets": []}
    aid = a["id"].replace("https://openalex.org/", "")
    # the author's own works on the topic → surface co-authors
    ow = _get("works", filter=f"author.id:{aid}", search=topic, per_page=25, sort="relevance_score:desc")
    coauth = {}
    own = []
    for w in ow.get("results", []):
        own.append(_work(w))
        for au in (w.get("authorships") or []):
            nm = au["author"]["display_name"]
            if nm.lower() != a["display_name"].lower():
                coauth[nm] = coauth.get(nm, 0) + 1
    coauthors = sorted(({"name": k, "shared": v} for k, v in coauth.items()), key=lambda x: -x["shared"])[:10]
    # datasets across this author+topic cluster (the payload: archived data with points)
    ds = works(topic + " " + a["display_name"].split()[-1], kind="dataset", limit=15)
    return {"author": a["display_name"], "openalex_id": aid, "topic": topic,
            "own_topic_works": own[:12], "coauthors": coauthors,
            "datasets": ds["results"], "note": "feed dataset DOIs to paper_data.extract for presence points."}


def describe():
    return {
        "connector": "litscout",
        "purpose": "Discover papers + archived DATASETS via the author co-authorship graph + topic (OpenAlex).",
        "produces": "ranked works/datasets with DOIs + the co-author cluster; bridge dataset DOIs to paper_data.",
        "functions": ["works(query, kind='dataset'|'article', india=False)",
                      "authors(query) -> co-authorship cluster (seed authors)",
                      "expand(author, topic) -> co-authors + their topic works + datasets"],
        "use": "For a LITERATURE / taxonomy / phylogeny / diet question, run this FIRST alongside "
               "paper_data: `works --kind dataset` to find archived data (points live there), `authors` to "
               "find the lab, `expand` to walk their co-authors' datasets. Then `paper_data.extract` the "
               "dataset DOIs for presence POINTS. Beats a title search — it walks the people + their data.",
        "gotcha": "OpenAlex is free (polite pool via mailto). `type:dataset` finds Zenodo/Dryad/figshare "
                  "records. A DOI here is a POINTER — extract the actual points with paper_data. India "
                  "filter = authored from an Indian institution (not where the species is).",
        "example": "python /opt/data/connectors/litscout.py works --query \"Uropeltis Eastern Ghats\" --kind dataset",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="litscout")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    w = sub.add_parser("works"); w.add_argument("--query", required=True)
    w.add_argument("--kind", choices=["dataset", "article"]); w.add_argument("--india", action="store_true")
    w.add_argument("--limit", type=int, default=25)
    au = sub.add_parser("authors"); au.add_argument("--query", required=True)
    ex = sub.add_parser("expand"); ex.add_argument("--author", required=True); ex.add_argument("--topic", required=True)
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    if args.cmd == "works":
        print(json.dumps(works(args.query, args.kind, args.india, args.limit), indent=2))
    elif args.cmd == "authors":
        print(json.dumps(authors(args.query), indent=2))
    elif args.cmd == "expand":
        print(json.dumps(expand(args.author, args.topic), indent=2))


if __name__ == "__main__":
    _main()
