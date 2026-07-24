"""indicators connector — bioindicator taxa for an ecological concern, grounded in GBIF.

Field teams (EBTL already tracks arachnids) use small, easy-to-survey taxa as SIGNALS of larger
ecological change. This connector maps a concern (soil health, forest recovery, water, pollination,
connectivity) to its established indicator taxa, then queries GBIF for what's actually recorded near
the site — turning "which insects tell us the soil is getting better?" into (a) the right taxa to
watch, cited, and (b) what data exists + what to go survey.

The taxon->indicator mapping is SOURCED ecology (citations below), NOT invented. The abundance/
presence numbers come from GBIF (real). Small sites are data-poor for arthropods, so the honest
output is usually "watch these groups + here's the sparse record + please survey them."

  indicators(concern, bbox) -> indicator taxa + GBIF records near site + why + survey ask

CLI:
  python -m connectors.indicators --describe
  python -m connectors.indicators --concern soil_health --bbox 78.170,12.721,78.197,12.747
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import occurrence  # noqa: E402  (reuse GBIF point producer)

# concern -> [(taxon scientificName for GBIF, common label, why it indicates, citation)]
# Sourced bioindicator ecology — cite these, do not present as our own claim.
CONCERNS = {
    "soil_health": [
        ("Scarabaeinae", "dung beetles", "dung burial / nutrient cycling; decline with soil & mammal loss", "Nichols et al. 2008; Spector 2006"),
        ("Formicidae", "ants", "soil turnover & disturbance; classic land-restoration indicator", "Andersen 1997; Underwood & Fisher 2006"),
        ("Collembola", "springtails", "decomposition & soil biological activity", "Rusek 1998"),
    ],
    "forest_recovery": [
        ("Nymphalidae", "brush-footed butterflies", "habitat structure & host-plant recovery", "Kerr 2000; Bonebrake 2010"),
        ("Araneae", "spiders", "vegetation structure & microhabitat (EBTL tracks these)", "Marc et al. 1999"),
        ("Cicadidae", "cicadas", "canopy & woody regrowth (acoustic-surveyable)", "general"),
    ],
    "water_quality": [
        ("Odonata", "dragonflies & damselflies", "freshwater & riparian condition", "Simaika & Samways 2011"),
        ("Anura", "frogs", "water + terrestrial linkage; pollution-sensitive", "Welsh & Ollivier 1998"),
    ],
    "pollination": [
        ("Apidae", "bees", "pollination function & floral resources", "Kremen et al. 2007"),
        ("Papilionidae", "swallowtail butterflies", "nectar & host plants", "general"),
    ],
    "connectivity": [
        ("Pycnonotidae", "bulbuls (frugivores)", "seed dispersal between patches (see ebird dispersers)", "general frugivory"),
        ("Bucerotidae", "hornbills", "long-distance seed dispersal where present", "general"),
    ],
}


def indicators(concern, bbox, years=None):
    """For a concern, list its sourced indicator taxa + GBIF records near the bbox."""
    key = concern.strip().lower().replace(" ", "_")
    taxa = CONCERNS.get(key)
    if not taxa:
        return {"error": f"unknown concern '{concern}'", "available": sorted(CONCERNS)}
    out = []
    for sci, label, why, cite in taxa:
        try:
            pts = occurrence.search(sci, bbox, limit=300, years=years)
            pts = pts if isinstance(pts, list) else pts.get("points", [])
            n = len(pts)
        except Exception:
            n = None
        out.append({"taxon": sci, "label": label, "indicates": why, "citation": cite,
                    "gbif_records_near_site": n})
    return {"concern": key, "aoi": bbox, "indicators": out,
            "note": "Indicator taxa = SOURCED ecology (citations). Record counts = GBIF (real, "
                    "effort-biased, sparse at small sites). Use to say WHICH groups to watch + what's "
                    "recorded + to REQUEST a targeted survey (e.g. dung-beetle pitfall traps, butterfly "
                    "transects, spider quadrats). A signal to instigate monitoring, not an authority claim."}


def describe():
    return {
        "connector": "indicators",
        "purpose": "Map an ecological concern to its SOURCED bioindicator taxa, then ground it in GBIF "
                   "records near the site — the right things to survey + what data exists.",
        "produces": "indicators(concern, bbox) -> indicator taxa + citations + GBIF counts + survey ask.",
        "functions": ["indicators(concern, bbox, years=None) -> per-taxon record counts + why + citation"],
        "concerns": sorted(CONCERNS),
        "use": "For 'which insects show soil is improving?' -> concern=soil_health. For butterflies/"
               "forest health -> forest_recovery. Pair with occurrence (trend over years), ebird "
               "(bird indicators/dispersers), phenology. EBTL already tracks arachnids -> forest_recovery.",
        "gotcha": "Taxon->indicator links are cited ecology, NOT our claim. GBIF is sparse at small "
                  "sites -> usually the answer is 'watch + survey these', a concrete data request.",
        "example": "python /opt/data/connectors/indicators.py --concern soil_health --bbox 78.170,12.721,78.197,12.747",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="indicators")
    ap.add_argument("--describe", action="store_true")
    ap.add_argument("--concern")
    ap.add_argument("--bbox")
    ap.add_argument("--years")
    args = ap.parse_args(argv)
    if args.describe or not args.concern or not args.bbox:
        print(json.dumps(describe(), indent=2)); return
    bbox = [float(x) for x in args.bbox.split(",")]
    print(json.dumps(indicators(args.concern, bbox, args.years), indent=2))


if __name__ == "__main__":
    _main()
