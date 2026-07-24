"""Scout — data-frontier discovery (NOTES.md Add 3).

Pushes the frontier OUTWARD: finds sources not in the corpus yet, VERIFIES they
actually return rows (phantom-data guard), and STAMPS provenance so access can be
requested later. License is recorded, never gated on.

Sources wired: GBIF (occurrence), IBP-via-GBIF (denser India data — IBP's own API
is bot-blocked, but it's a GBIF publisher so route through publishingOrg), Zenodo
(research records), CKAN (catalogs), and analog-ecoregion pulls (same ecoregion
outside the AOI, tagged aoi_status=analog_ecoregion). Stdlib only (urllib); EE-
backed analog *points* go through the ecoregion connector, not here.
"""
import csv as _csv
import io
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

GBIF = "https://api.gbif.org/v1/occurrence/search"
ZENODO = "https://zenodo.org/api/records"
# SoIB 2023 (State of India's Birds) — per-state species trend/status, CC-BY.
SOIB_TN = "https://zenodo.org/api/records/11124590/files/SoIB%202023%20Tamil%20Nadu.csv/content"


def _get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "idlisseus-scout/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _get_text(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": "idlisseus-scout/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _stamp(source_url, extra=None):
    """Provenance stamp — the mandatory lineage (Add 3 rule 1)."""
    p = {"source_url": source_url,
         "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "author_contact": None, "license": "unknown"}   # license recorded, never gated
    if extra:
        p.update(extra)
    return p


def _gbif_count(bbox, **extra):
    w, s, e, n = bbox
    params = {"hasCoordinate": "true", "decimalLatitude": f"{s},{n}",
              "decimalLongitude": f"{w},{e}", "limit": 0, **extra}
    url = f"{GBIF}?{urllib.parse.urlencode(params)}"
    return _get(url).get("count", 0), url


def gbif_species(species, bbox, publishing_org=None, ref="GBIF"):
    """Verify + count occurrences of `species` in bbox. publishing_org routes IBP.
    verified_queryable=False (phantom) if 0 rows."""
    extra = {"scientificName": species}
    if publishing_org:
        extra["publishingOrg"] = publishing_org
    try:
        count, url = _gbif_count(bbox, **extra)
    except Exception as ex:
        return {"kind": "connector", "ref": ref, "target": species,
                "verified_queryable": False, "error": str(ex), "provenance": _stamp(GBIF)}
    return {"kind": "connector", "ref": ref, "target": species, "n_records": count,
            "verified_queryable": count > 0,
            "note": "usable now via occurrence.search" if count > 0
                    else "no records in AOI — discard/flag, do not treat as data",
            "provenance": _stamp(url, {"license": "CC-BY (GBIF, cite datasetKeys)"})}


def zenodo_records(query, size=3):
    """Discover research records (papers/datasets) on Zenodo. Significant tokens
    are AND-joined so the count is real recall, not OR-matched common-word noise."""
    toks = re.findall(r"[A-Za-z]{4,}", query)
    q = " AND ".join(toks) if toks else query
    url = f"{ZENODO}?" + urllib.parse.urlencode({"q": q, "size": size})
    try:
        d = _get(url)
    except Exception as ex:
        return {"kind": "research", "ref": "Zenodo", "query": query,
                "verified_queryable": False, "error": str(ex), "provenance": _stamp(url)}
    hits = d.get("hits", {})
    sample = [{"title": h.get("metadata", {}).get("title"),
               "doi": h.get("doi"), "url": h.get("links", {}).get("self_html")}
              for h in hits.get("hits", [])]
    return {"kind": "research", "ref": "Zenodo", "query": query,
            "n_total": hits.get("total", 0), "sample": sample,
            "verified_queryable": hits.get("total", 0) > 0, "provenance": _stamp(url)}


def ckan_search(base, query, rows=3):
    """Discover datasets on any CKAN instance via the uniform package_search API."""
    url = f"{base.rstrip('/')}/api/3/action/package_search?" + urllib.parse.urlencode(
        {"q": query, "rows": rows})
    try:
        res = _get(url).get("result", {})
    except Exception as ex:
        return {"kind": "catalog", "ref": base, "query": query,
                "verified_queryable": False, "error": str(ex), "provenance": _stamp(url)}
    hits = [{"title": p.get("title"), "url": f"{base.rstrip('/')}/dataset/{p.get('name')}",
             "n_resources": len(p.get("resources", [])),
             "license": p.get("license_title") or "unknown"} for p in res.get("results", [])]
    return {"kind": "catalog", "ref": base, "query": query, "n_total": res.get("count", 0),
            "returned": len(hits), "hits": hits, "verified_queryable": len(hits) > 0,
            "provenance": _stamp(url)}


def soib_status(species_list, csv_url=SOIB_TN):
    """Real Indian dataset: SoIB 2023 national priority/trend/IUCN per bird species.
    Answers 'which of our recorded birds are of conservation concern' without a model."""
    try:
        raw = _get_text(csv_url)
    except Exception as ex:
        return {"kind": "bird_status", "ref": "SoIB 2023", "verified_queryable": False,
                "error": str(ex), "provenance": _stamp(csv_url)}
    idx = {}
    for r in _csv.DictReader(io.StringIO(raw)):
        for k in ("Scientific Name", "eBird Scientific Name 2022"):
            if r.get(k):
                idx[r[k].strip().lower()] = r
    out = []
    for sp in species_list:
        r = idx.get(sp.strip().lower())
        out.append({"species": sp, "priority": r["SoIB 2023 Priority Status"],
                    "long_term_trend": r["SoIB 2023 Long-term Trend Status"],
                    "current_trend": r["SoIB 2023 Current Annual Trend Status"],
                    "iucn": r["IUCN Category"]} if r else {"species": sp, "matched": False})
    return {"kind": "bird_status", "ref": "SoIB 2023 (Zenodo 11124590)",
            "n_matched": sum(1 for o in out if o.get("priority")), "results": out,
            "verified_queryable": any(o.get("priority") for o in out),
            "provenance": _stamp(csv_url, {"license": "CC-BY 4.0 (SoIB / Bird Count India)"})}


def analog_discovery(aoi):
    """Same-ecoregion sites outside the AOI: aggregate GBIF density + research.
    Everything here is tagged aoi_status=analog_ecoregion so it's never mistaken
    for an in-AOI result (Add 3 out-of-AOI honesty)."""
    out = []
    for site in aoi.get("analog_sites", []):
        try:
            count, url = _gbif_count([float(x) for x in site["bbox"]])
        except Exception as ex:
            out.append({"site": site["name"], "aoi_status": "analog_ecoregion",
                        "verified_queryable": False, "error": str(ex)})
            continue
        out.append({"site": site["name"], "bbox": site["bbox"],
                    "aoi_status": "analog_ecoregion", "ecoregion": aoi.get("ecoregion"),
                    "gbif_records": count, "verified_queryable": count > 0,
                    "research": zenodo_records(site["name"], size=2),
                    "provenance": _stamp(url)})
    return out


def discover(aoi):
    """Full discovery pass for one AOI."""
    bbox = [float(x) for x in aoi["bbox"]]
    ibp = aoi.get("ibp_org")
    species = []
    for sp in aoi.get("seed_species", []):
        rec = gbif_species(sp, bbox)
        if ibp:                                  # denser India via IBP-through-GBIF
            rec["ibp"] = gbif_species(sp, bbox, publishing_org=ibp, ref="IBP-via-GBIF")
        species.append(rec)
    available = [s for s in species if s.get("verified_queryable")
                 or s.get("ibp", {}).get("verified_queryable")]
    phantom = [s for s in species if s not in available]

    kw = {"invasives": "invasive species", "fire": "forest fire", "water": "reservoir water",
          "connectivity": "wildlife corridor elephant", "landuse": "land use land cover",
          "biodiversity": "biodiversity", "restoration": "afforestation restoration",
          "governance": "protected area"}
    top_buckets = [b for b, _ in sorted(aoi.get("buckets", {}).items(), key=lambda kv: -kv[1])[:4]]
    catalogs = [{"bucket": b, **ckan_search(cat["base"], kw.get(b, b))}
                for cat in aoi.get("catalogs", []) if cat.get("type") == "ckan"
                for b in top_buckets]
    research = [zenodo_records(f"{kw.get(b, b)} India") for b in top_buckets[:2]]
    birds = soib_status(aoi["flagship_birds"]) if aoi.get("flagship_birds") else None

    return {"aoi": aoi["name"], "available": available, "phantom": phantom,
            "catalogs": catalogs, "research": research, "bird_status": birds,
            "analog": analog_discovery(aoi)}
