"""ebird connector — eBird bird observations + hotspots (a 'login' connector: free API key).

eBird is the richest bird-occurrence source for a specific site (Varun's EBTL has an eBird
hotspot: L36453021). Unlike GBIF, eBird gives per-hotspot recent observations, full species
lists, and hotspot coordinates — so it both PRODUCES bird points and can ANCHOR a site.

Auth: eBird's API needs a free key (the web pages are bot-protected). Key resolution order:
env EBIRD_API_KEY, then ~/.hermes/secrets/ebird.json (Hermes sandbox), then
~/.config/idlisseus/ebird.json (host) — each {"api_key": "..."}. Get one instantly at
https://ebird.org/api/keygen (needs an eBird/Cornell account login).

POINT PRODUCER:
  observations(loc_id=..., back=30) -> recent bird points at a hotspot
  observations(bbox=[w,s,e,n], back=30) -> recent bird points in an area
  hotspot_info(loc_id) -> {name, lat, lon, n_species}  (anchors a site)
  species_list(loc_id) -> species recorded at the hotspot

CLI:
  python -m connectors.ebird --describe
  python -m connectors.ebird hotspot --loc L36453021
  python -m connectors.ebird obs --loc L36453021 --back 30 --out /opt/data/work/birds.csv
  python -m connectors.ebird obs --bbox 78.170,12.721,78.197,12.747 --out /opt/data/work/birds.csv
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import write_points  # noqa: E402

API = "https://api.ebird.org/v2"
_CRED_PATHS = [os.path.expanduser("~/.hermes/secrets/ebird.json"),
               os.path.expanduser("~/.config/idlisseus/ebird.json")]


def _key():
    k = os.environ.get("EBIRD_API_KEY")
    if k:
        return k
    for p in _CRED_PATHS:
        if os.path.exists(p):
            try:
                return json.load(open(p)).get("api_key")
            except Exception:
                continue
    return None


def configured():
    return bool(_key())


def _warn_unconfigured():
    sys.stderr.write(
        "\n*** ebird: no API key — this connector is DISABLED. Get a free key at "
        "https://ebird.org/api/keygen and put it in ~/.config/idlisseus/ebird.json "
        '{"api_key":"..."} (or env EBIRD_API_KEY). See DRYAD_SETUP.md for the pattern.\n\n')


def _get(path, params=None):
    key = _key()
    if not key:
        _warn_unconfigured()
        raise RuntimeError("ebird: no API key configured")
    url = f"{API}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"X-eBirdApiToken": key,
                                               "User-Agent": "idlisseus-ebird/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def hotspot_info(loc_id):
    """Hotspot coordinates + species count — anchors a site (e.g. EBTL = L36453021)."""
    d = _get(f"ref/hotspot/info/{loc_id}")
    return {"loc_id": loc_id, "name": d.get("name"),
            "lat": d.get("latitude"), "lon": d.get("longitude"),
            "n_species": d.get("numSpeciesAllTime"),
            "region": d.get("subnational1Name") or d.get("subnational1Code")}


def _obs_rows(raw):
    rows = []
    for o in raw:
        if o.get("lat") is None or o.get("lng") is None:
            continue
        rows.append({"lat": round(o["lat"], 6), "lon": round(o["lng"], 6),
                     "species": o.get("comName") or o.get("sciName"),
                     "sci_name": o.get("sciName"), "count": o.get("howMany"),
                     "date": o.get("obsDt"), "loc_id": o.get("locId")})
    return rows


def observations(loc_id=None, bbox=None, back=30, max_results=1000):
    """Recent bird observations as points — at a hotspot (loc_id) or in an area (bbox)."""
    if loc_id:
        return _obs_rows(_get(f"data/obs/{loc_id}/recent", {"back": back, "maxResults": max_results}))
    if bbox:
        w, s, e, n = [float(x) for x in bbox]
        lat, lng = (s + n) / 2, (w + e) / 2
        # dist = half-diagonal in km (eBird caps at 50 km)
        dist = min(50, max(1, int(111 * max(n - s, e - w) / 2) + 1))
        return _obs_rows(_get("data/obs/geo/recent",
                              {"lat": round(lat, 4), "lng": round(lng, 4), "dist": dist,
                               "back": back, "maxResults": max_results}))
    raise ValueError("observations needs loc_id or bbox")


def species_list(loc_id):
    """Species codes ever recorded at the hotspot."""
    return _get(f"product/spplist/{loc_id}")


def _names_for(codes):
    """Map eBird species codes -> common names via the taxonomy endpoint."""
    if not codes:
        return []
    tax = _get("ref/taxonomy/ebird", {"fmt": "json", "species": ",".join(codes)})
    by = {t["speciesCode"]: t.get("comName", t["speciesCode"]) for t in tax}
    return [by.get(c, c) for c in codes]


# Frugivore / seed-disperser guilds — families whose members are significant fleshy-fruit
# dispersers in Indian dry/deciduous systems (bulbuls, mynas, koel, barbets, white-eyes,
# starlings, orioles, leafbirds, flowerpeckers, hornbills, green-pigeons are classic Lantana
# camara dispersers per the Indian frugivory literature). Heuristic by name; VERIFY specifics
# via paper_data. This is the BIRD->PLANT bridge, not authority.
_DISPERSER_TERMS = ("bulbul", "myna", "mynah", "koel", "barbet", "white-eye", "starling",
                    "oriole", "leafbird", "flowerpecker", "hornbill", "green-pigeon",
                    "green pigeon", "iora", "fairy-bluebird")
_LANTANA_DISPERSERS = ("bulbul", "myna", "mynah", "koel", "barbet", "white-eye", "starling")
_NOT_FRUG = ("buzzard", "eagle", "hawk", "kite", "falcon", "owl")  # name-match guards


def frugivore_dispersers(loc_id):
    """The BIRD->PLANT bridge: recorded frugivorous seed-dispersers at a hotspot. Birds that eat
    fleshy fruit disperse seeds — including invasive Lantana camara. When direct plant/invasive
    data at a site is scarce (common), the abundant bird list still carries a MECHANISTIC signal
    for invasive spread, seed rain, and connectivity (which birds move where). Returns disperser
    species present + which are documented Lantana dispersers. GROUNDING: general Indian frugivory
    literature — a correlate/hypothesis to instigate targeted data, NOT an authority claim; verify
    diets via paper_data, and annotate bird points with landcover to recover the habitat eBird lacks."""
    names = _names_for(species_list(loc_id))
    disp = [n for n in names if any(t in n.lower() for t in _DISPERSER_TERMS)
            and not any(x in n.lower() for x in _NOT_FRUG)]
    lantana = [n for n in disp if any(t in n.lower() for t in _LANTANA_DISPERSERS)]
    return {"loc_id": loc_id, "n_species": len(names), "n_dispersers": len(disp),
            "dispersers": disp, "lantana_dispersers": lantana,
            "bridge_note": "These frugivores disperse fleshy-fruit seeds incl. invasive Lantana — a "
                           "correlate for invasive spread + connectivity where direct plant data is "
                           "scarce. Correlation, not authority. Next data: verify diets via paper_data; "
                           "annotate bird points with landcover for habitat; ask birders to log fruiting "
                           "plants / run plant surveys at bird-dense spots."}


def describe():
    return {
        "connector": "ebird",
        "purpose": "eBird bird observations + hotspot info (per-site bird occurrence). AUTH: free "
                   "API key (https://ebird.org/api/keygen); a 'login' connector.",
        "produces": "observations(loc_id|bbox)->bird points; hotspot_info(loc_id)->coords+n_species.",
        "functions": [
            "hotspot_info(loc_id) -> {name, lat, lon, n_species} (anchors a site)",
            "observations(loc_id=.., back=30) -> recent bird points at a hotspot",
            "observations(bbox=[w,s,e,n], back=30) -> recent bird points in an area",
            "species_list(loc_id) -> species recorded",
            "frugivore_dispersers(loc_id) -> BIRD->PLANT bridge: recorded frugivores that disperse "
            "seeds (incl. invasive Lantana) — a mechanistic correlate when direct plant data is scarce",
        ],
        "use": "EBTL hotspot = L36453021. Anchor the site with hotspot_info; observations as a "
               "POINT PRODUCER (annotate with landcover/terrain, or feed predict). When BIRDS are the "
               "abundant dataset and the question is about plants/invasives/connectivity, use "
               "frugivore_dispersers as a bridge (birds->diet->dispersal), then say so honestly + ask "
               "for the plant/habitat data that would confirm it. eBird has NO habitat field -> recover "
               "it by annotating bird points with landcover.",
        "gotcha": "Needs a free API key (configured()==False if unset -> warns loudly). eBird 'recent' "
                  "is last-N-days only; sampling is effort-biased (birders visit accessible spots).",
        "example": "python /opt/data/connectors/ebird.py obs --loc L36453021 --back 30",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="ebird")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    h = sub.add_parser("hotspot"); h.add_argument("--loc", required=True)
    o = sub.add_parser("obs"); o.add_argument("--loc"); o.add_argument("--bbox")
    o.add_argument("--back", type=int, default=30); o.add_argument("--out")
    sp = sub.add_parser("spplist"); sp.add_argument("--loc", required=True)
    fd = sub.add_parser("dispersers"); fd.add_argument("--loc", required=True)
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    if args.cmd == "hotspot":
        print(json.dumps(hotspot_info(args.loc), indent=2))
    elif args.cmd == "obs":
        bbox = [float(x) for x in args.bbox.split(",")] if args.bbox else None
        rows = observations(loc_id=args.loc, bbox=bbox, back=args.back)
        if args.out:
            write_points(rows, args.out)
            print(f"wrote {len(rows)} points -> {args.out}")
        else:
            print(json.dumps(rows, indent=2))
    elif args.cmd == "spplist":
        print(json.dumps(species_list(args.loc), indent=2))
    elif args.cmd == "dispersers":
        print(json.dumps(frugivore_dispersers(args.loc), indent=2))


if __name__ == "__main__":
    _main()
