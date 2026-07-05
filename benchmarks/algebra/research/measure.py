"""measure.py — turn an extracted indicator into a REAL data reading (or an honest
gap), routed by its `measurable_via` tag. No fabrication: every value comes from a
live API/connector and carries a source. A gap is recorded as a gap, with a
suggestion for what to collect / where to look next.
"""
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, __file__.rsplit("/", 2)[0] + "/components")
import scout  # noqa: E402

GBIF = "https://api.gbif.org/v1/occurrence/search"


def _get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "idlisseus-research/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _stamp(url):
    return {"source_url": url,
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def gbif_by_year(species, bbox):
    """Yearly GBIF occurrence counts + a 'showing up / increasing' read. This is the
    engine for 'is invasive X appearing?'."""
    w, s, e, n = bbox
    q = urllib.parse.urlencode({"hasCoordinate": "true", "scientificName": species,
                                "decimalLatitude": f"{s},{n}", "decimalLongitude": f"{w},{e}",
                                "facet": "year", "facetLimit": 40, "limit": 0})
    url = f"{GBIF}?{q}"
    try:
        d = _get(url)
    except Exception as ex:
        return {"gap": True, "reason": f"gbif error: {ex}"}
    years = {int(c["name"]): c["count"] for f in d.get("facets", [])
             if f["field"] == "YEAR" for c in f["counts"] if c["name"].isdigit()}
    total = d.get("count", 0)
    if not years:
        return {"measured": False, "total_records": total,
                "note": "no dated records in AOI", "source": "GBIF", "provenance": _stamp(url)}
    recent = sum(v for y, v in years.items() if y >= 2020)
    prior = sum(v for y, v in years.items() if 2014 <= y < 2020)
    trend = ("appearing/increasing" if recent > prior else
             "present, not increasing" if recent else "only older records")
    return {"measured": True, "total_records": total, "first_year": min(years),
            "recent_2020plus": recent, "prior_2014_2019": prior, "trend": trend,
            "by_year": dict(sorted(years.items())), "source": "GBIF (incl. eBird/iNaturalist)",
            "provenance": _stamp(url)}


def gbif_top_species(bbox, n=15):
    """Discover the most-recorded species in an AOI (GBIF species facet -> names).
    Turns idle time into a real per-AOI biodiversity catalog."""
    w, s, e, nn = bbox
    q = urllib.parse.urlencode({"hasCoordinate": "true", "decimalLatitude": f"{s},{nn}",
                                "decimalLongitude": f"{w},{e}", "limit": 0,
                                "facet": "speciesKey", "facetLimit": n})
    try:
        d = _get(f"{GBIF}?{q}")
    except Exception:
        return []
    keys = [c["name"] for f in d.get("facets", []) if f["field"] == "SPECIES_KEY"
            for c in f["counts"]]
    names = []
    for k in keys[:n]:
        try:
            sp = _get(f"https://api.gbif.org/v1/species/{k}")
            nm = sp.get("canonicalName") or sp.get("scientificName")
            if nm:
                names.append(nm)
        except Exception:
            continue
    return names


def ckan_socioeconomic(query):
    """Look for a real gov/NGO socioeconomic dataset (livelihoods etc.)."""
    r = scout.ckan_search("https://data.gov.in", query, rows=3)
    if r.get("verified_queryable"):
        return {"measured": "dataset_found", "hits": r.get("hits"), "source": "data.gov.in",
                "provenance": r.get("provenance")}
    return {"gap": True, "reason": "no open socioeconomic dataset matched",
            "suggestion": "gov Census/DES village data or EBTL's own women's-collective "
                          "records; likely field-collect."}


def measure(indicator, aoi, map_indicators=None):
    """Route one indicator to real data. map_indicators = precomputed satellite
    readings for the AOI (greening/fire/landcover), passed in so we don't re-run EE
    per indicator."""
    via = (indicator.get("measurable_via") or "unknown").lower()
    bbox = [float(x) for x in aoi["bbox"]]

    if via == "species_occurrence":
        sp = _guess_species(indicator, aoi)
        r = gbif_by_year(sp, bbox)
        r["species_used"] = sp
        return r
    if via == "bird_trend_dataset":
        birds = aoi.get("flagship_birds", [])
        return {**scout.soib_status(birds), "measured": True} if birds else \
            {"gap": True, "reason": "no bird list on AOI"}
    if via == "satellite_timeseries":
        if map_indicators:
            return {"measured": True, "source": "Earth Engine connectors (precomputed)",
                    **map_indicators}
        return {"gap": True, "reason": "satellite connector not run for this AOI"}
    if via == "socioeconomic_dataset":
        return ckan_socioeconomic(indicator.get("indicator", ""))
    # field_survey / unknown
    return {"gap": True, "reason": f"measurable_via={via}: needs field data or a new connector",
            "suggestion": "check the paper's own Zenodo CSV, an analog-site survey, "
                          "or collect it (see DATA_ASSESSMENT collect-list)."}


_INVASIVE = ("lantana", "prosopis", "chromolaena", "parthenium", "senna")


def _guess_species(indicator, aoi):
    """Pick the species an occurrence indicator is about."""
    txt = (indicator.get("indicator", "") + " " + indicator.get("question", "")).lower()
    for sp in aoi.get("seed_species", []):
        if sp.split()[0].lower() in txt or (len(sp.split()) > 1 and sp.split()[1].lower() in txt):
            return sp
    for marker in _INVASIVE:
        if marker in txt:
            return next((s for s in aoi.get("seed_species", []) if marker in s.lower()),
                        "Lantana camara")
    return aoi.get("seed_species", ["Lantana camara"])[0]
