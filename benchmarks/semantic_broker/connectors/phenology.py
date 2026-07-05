"""phenology connector — empirical flowering/fruiting calendar from GBIF (no key).

The NURSERY angle: to supply native saplings you must collect seed when it's available, i.e.
know WHEN a species fruits. GBIF/iNaturalist records carry `reproductiveCondition` annotations
("flowers", "fruits or seeds") + a month — so the month-distribution of annotated records is an
empirical phenology, for ANY species (dry-deciduous or wet), grounded in real observations.

Works for the seed-collection → propagation → monsoon-planting calendar. It is CROWD-SOURCED
(iNaturalist-biased, observer-biased) — report months + sample size + that caveat, never as a
definitive calendar.

  phenology(species, country='IN') -> {fruiting_months, flowering_months, calendar, n_annotated}

CLI:
  python -m connectors.phenology --species "Syzygium cumini"          # jamun
  python -m connectors.phenology --species "Azadirachta indica" --country IN
"""
import argparse
import collections
import json
import os
import sys
import urllib.parse
import urllib.request

API = "https://api.gbif.org/v1/occurrence/search"
_MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# common-name hints (Hermes usually passes scientific; a few dry-deciduous natives for convenience)
COMMON = {"jamun": "Syzygium cumini", "neem": "Azadirachta indica", "tamarind": "Tamarindus indica",
          "banyan": "Ficus benghalensis", "peepal": "Ficus religiosa", "amla": "Phyllanthus emblica",
          "sandalwood": "Santalum album", "flame of the forest": "Butea monosperma",
          "indian gooseberry": "Phyllanthus emblica", "arjun": "Terminalia arjuna"}


def _get(params):
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": "idlisseus-phenology/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def phenology(species, country="IN", pages=4, per=300):
    """Empirical flowering/fruiting months for `species` from GBIF reproductiveCondition."""
    sci = COMMON.get(species.strip().lower(), species)
    total = None
    fruit, flower = collections.Counter(), collections.Counter()
    n_anno = 0
    for pg in range(pages):
        p = {"scientificName": sci, "hasCoordinate": "true", "limit": per, "offset": pg * per}
        if country:
            p["country"] = country
        try:
            d = _get(p)
        except Exception:
            break
        if total is None:
            total = d.get("count", 0)
        for r in d.get("results", []):
            rc = str(r.get("reproductiveCondition") or "").lower()
            m = r.get("month")
            if not m or not rc or rc.startswith("no "):
                continue
            n_anno += 1
            if "fruit" in rc or "seed" in rc:
                fruit[m] += 1
            if "flower" in rc:
                flower[m] += 1
        if not d.get("results") or (pg + 1) * per >= (total or 0):
            break

    def top(counter):
        return [_MONTHS[m] for m, _ in counter.most_common(3)]
    return {"species": sci, "country": country, "n_records": total, "n_annotated": n_anno,
            "fruiting_months": top(fruit), "flowering_months": top(flower),
            "fruiting_by_month": {_MONTHS[m]: c for m, c in sorted(fruit.items())},
            "flowering_by_month": {_MONTHS[m]: c for m, c in sorted(flower.items())},
            "caveat": "Crowd-sourced phenology (GBIF/iNaturalist) — observer-biased, month-binned. "
                      "Report peak months + sample size (n_annotated); use to time SEED COLLECTION "
                      "for the nursery, then propagate for the planting window. Not a definitive calendar; "
                      "confirm with local nursery/field notes."}


def describe():
    return {
        "connector": "phenology",
        "purpose": "Empirical flowering/fruiting calendar per species from GBIF reproductiveCondition — "
                   "the nursery's seed-collection timing, data-grounded, any species, no key.",
        "produces": "phenology(species) -> fruiting_months + flowering_months + per-month counts.",
        "functions": ["phenology(species, country='IN') -> months + n_annotated + caveat"],
        "use": "NURSERY planning: which native to collect seed for NOW (fruiting_months), then "
               "propagate for the planting window (Krishnagiri = NE monsoon, ~Oct-Dec). Pair with "
               "occurrence (is it recorded near the site?) and traits (seed size/dispersal).",
        "gotcha": "Crowd-sourced & observer-biased; needs enough annotated records (n_annotated). "
                  "Common names accepted for a few natives; otherwise pass the scientific name.",
        "example": "python /opt/data/connectors/phenology.py --species 'Syzygium cumini'",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="phenology")
    ap.add_argument("--describe", action="store_true")
    ap.add_argument("--species")
    ap.add_argument("--country", default="IN")
    args = ap.parse_args(argv)
    if args.describe or not args.species:
        print(json.dumps(describe(), indent=2)); return
    print(json.dumps(phenology(args.species, args.country), indent=2))


if __name__ == "__main__":
    _main()
