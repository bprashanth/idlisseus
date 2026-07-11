"""paper_data connector — ingest the DATASETS/codebooks inside research papers.

The under-tapped source: Zenodo/Dryad datasets attached to papers carry presence
points, plot measurements, soil pH, traits, etc. — even from nearby areas, usable
as proxy/extrapolation. This connector finds them (curated communities first, not
noisy full-text), downloads the tables, and extracts labelled points — returning
them like `occurrence` does, tagged by whether they're in the AOI, near it, or in
an analog ecoregion.

Pure-python (urllib/csv) so it runs anywhere. The hard, messy step — mapping a
dataset's columns to {coordinates, value} and pulling a value out of a free-text
field ("... Elephant Sighting") — is done heuristically here and is the exact step
to harden via Hermes trace-mining (see RESEARCH/NEXT_STEPS).

  find(community|query) -> datasets with tabular files
  ingest(file_url)      -> {coords, value candidates, extracted points} (JUDGE this)
  search(variable, aoi) -> points for a variable, tagged aoi_status
"""
import csv
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# curated communities (clean) — add ATREE/Keystone/India ecology as found.
COMMUNITIES = {"ncf": "c1433757-a33b-4873-a1cc-35d43746597c"}
ZENODO = "https://zenodo.org/api/records"

# ---- Dryad (authenticated source) --------------------------------------------------
# Dryad search/metadata is open, but downloading file BYTES needs an OAuth bearer token.
# This is our first "login" connector: creds live OUTSIDE the repo (never committed).
# Read order: env DRYAD_CLIENT_ID/SECRET, then ~/.hermes/secrets/dryad.json (uid-10000,
# for the Hermes sandbox — same spirit as EE creds), then ~/.config/idlisseus/dryad.json
# (host-owned, for the host-side crawl). Get creds by logging into datadryad.org (ORCID)
# once and generating them at /account. Token (10h) via client_credentials, cached
# best-effort (host crawl may not be able to write ~/.hermes; that's fine — it re-mints).
DRYAD = "https://datadryad.org"
_CRED_PATHS = [os.path.expanduser("~/.hermes/secrets/dryad.json"),
               os.path.expanduser("~/.config/idlisseus/dryad.json")]
_TOKEN_CACHE = os.path.expanduser("~/.config/idlisseus/dryad_token.json")
_TOKEN_MEM = {}  # in-process cache so one crawl mints once even if disk is unwritable


def _dryad_creds():
    cid, sec = os.environ.get("DRYAD_CLIENT_ID"), os.environ.get("DRYAD_CLIENT_SECRET")
    if cid and sec:
        return cid, sec
    for p in _CRED_PATHS:
        if os.path.exists(p):
            try:
                d = json.load(open(p))
                if d.get("client_id") and d.get("client_secret"):
                    return d["client_id"], d["client_secret"]
            except Exception:
                continue
    return None, None


def _dryad_token():
    """client_credentials -> 10h bearer, cached (memory + best-effort disk). None if unset."""
    if _TOKEN_MEM.get("exp", 0) > time.time() + 120:
        return _TOKEN_MEM["token"]
    if os.path.exists(_TOKEN_CACHE):
        try:
            d = json.load(open(_TOKEN_CACHE))
            if d.get("exp", 0) > time.time() + 120:
                _TOKEN_MEM.update(d)
                return d["token"]
        except Exception:
            pass
    cid, sec = _dryad_creds()
    if not cid or not sec:
        return None
    body = urllib.parse.urlencode({"client_id": cid, "client_secret": sec,
                                   "grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(DRYAD + "/oauth/token", body,
                                 {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
    d = json.loads(urllib.request.urlopen(req, timeout=30).read())
    rec = {"token": d["access_token"], "exp": time.time() + d.get("expires_in", 36000)}
    _TOKEN_MEM.update(rec)
    try:
        os.makedirs(os.path.dirname(_TOKEN_CACHE), exist_ok=True)
        json.dump(rec, open(_TOKEN_CACHE, "w"))
    except Exception:
        pass  # unwritable (e.g. host under uid-10000 HOME) — memory cache still holds
    return rec["token"]


def dryad_configured():
    return bool(_dryad_creds()[0])

_LAT = ("decimallatitude", "latitude", "lat_gps", "lat", "y_coord", "ycoord", "y", "gps_lat")
_LON = ("decimallongitude", "longitude", "long_gps", "lon", "lng", "long", "x_coord",
        "xcoord", "x", "gps_lon", "gps_long")
_TEXT_FIELDS = ("title", "event", "eventremarks", "remarks", "notes", "description",
                "occurrenceremarks", "comments", "habitat", "verbatimlocality")
_SPECIES_COLS = ("scientificname", "species", "taxon", "taxonname", "binomial",
                 "species_name", "vernacularname", "commonname")
# numeric env/trait value columns worth transferring (soil, plot measurements, ...)
_VALUE_HINTS = ("ph", "soil", "dbh", "height", "canopy", "cover", "biomass", "carbon",
                "girth", "density", "basal", "nitrogen", "moisture", "temperature",
                "rainfall", "elevation", "slope", "litter", "abundance", "count")
# known taxa markers to pull a species out of free text
_TAXA = ("elephant", "tiger", "leopard", "gaur", "sloth bear", "bear", "tahr", "langur",
         "macaque", "dhole", "sambar", "chital", "hornbill", "lion-tailed", "civet",
         "porcupine", "pangolin", "mouse deer", "barking deer", "giant squirrel",
         "lantana", "prosopis", "chromolaena", "python", "cobra", "viper")


class _StripAuthOnRedirect(urllib.request.HTTPRedirectHandler):
    """Dryad's /download 302-redirects to a PRESIGNED S3 url (auth already in the query
    string). urllib re-sends our bearer across the redirect and S3 rejects the double
    auth ('Only one auth mechanism allowed'), so drop Authorization on redirect."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        newreq = super().redirect_request(req, fp, code, msg, headers, newurl)
        if newreq is not None:
            newreq.headers.pop("Authorization", None)
            newreq.headers.pop("authorization", None)
        return newreq


_OPENER = urllib.request.build_opener(_StripAuthOnRedirect)


def _get(url, timeout=45):
    if url.startswith("/") and os.path.exists(url):       # local file (unzipped cache)
        return open(url, "rb").read()
    headers = {"User-Agent": "idlisseus-paperdata/0.1"}
    if "datadryad.org" in url:                            # authenticated + rate-limited
        tok = _dryad_token()
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers)
            with _OPENER.open(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:             # Dryad rate-limit: back off
                time.sleep(2 ** attempt * 2)
                continue
            raise


def _getj(url, timeout=45):
    return json.loads(_get(url, timeout))


def find(query=None, community="ncf", size=25):
    """Datasets with tabular files, from a curated community (clean) or a query."""
    params = {"size": size, "type": "dataset"}
    if community in COMMUNITIES:
        params["communities"] = COMMUNITIES[community]
    if query:
        params["q"] = query
    d = _getj(f"{ZENODO}?{urllib.parse.urlencode(params)}")
    out = []
    for h in d.get("hits", {}).get("hits", []):
        files = [{"name": f.get("key"), "size_mb": round(f.get("size", 0) / 1e6, 3),
                  "url": f.get("links", {}).get("self")}
                 for f in h.get("files", [])
                 if str(f.get("key", "")).lower().endswith((".csv", ".tsv", ".txt"))]
        if files:
            out.append({"title": h.get("metadata", {}).get("title"), "doi": h.get("doi"),
                        "url": h.get("links", {}).get("self_html"), "files": files})
    return out


_TAB_EXT = (".csv", ".tsv", ".txt", ".xlsx", ".xls")


_warned_dryad = [False]


def _warn_dryad_unconfigured():
    if not _warned_dryad[0]:
        _warned_dryad[0] = True
        sys.stderr.write(
            "\n*** paper_data: Dryad credentials NOT configured — search works but FILE "
            "DOWNLOADS WILL FAIL (HTTP 401). The Dryad half of this skill is disabled.\n"
            "    Fix: benchmarks/algebra/research/DRYAD_SETUP.md (creds -> "
            "~/.config/idlisseus/dryad.json). Zenodo/NCF still work without it.\n\n")


def dryad_find(query, size=20):
    """Search Dryad and return datasets with per-file DOWNLOAD urls (bytes need a token;
    see dryad_configured()). Same shape as find() so it drops into ingest_dataset/search."""
    if not dryad_configured():
        _warn_dryad_unconfigured()
    d = _getj(DRYAD + "/api/v2/search?" + urllib.parse.urlencode({"q": query, "per_page": size}))
    out = []
    for x in d.get("_embedded", {}).get("stash:datasets", []):
        doi = x.get("identifier")
        vhref = x.get("_links", {}).get("stash:version", {}).get("href")
        if not doi or not vhref:
            continue
        try:
            fl = _getj(DRYAD + vhref + "/files")
        except Exception:
            continue
        files = []
        for f in fl.get("_embedded", {}).get("stash:files", []):
            path = f.get("path", "")
            href = f.get("_links", {}).get("stash:download", {}).get("href")
            if href and path.lower().endswith(_TAB_EXT) and f.get("size", 0) < 60e6:
                files.append({"name": path, "size_mb": round(f.get("size", 0) / 1e6, 3),
                              "url": DRYAD + href})
        if files:
            out.append({"title": x.get("title"), "doi": doi,
                        "url": DRYAD + x.get("_links", {}).get("self", {}).get("href", ""),
                        "authors": [f"{a.get('lastName','')} {a.get('firstName','')}".strip()
                                    for a in x.get("authors", [])],
                        "files": files})
    return out


def _read_table(url, max_rows=100000):
    name = url.lower()
    raw = _get(url)
    if name.endswith((".xlsx", ".xls")):                  # Excel via openpyxl
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        it = wb.active.iter_rows(values_only=True)
        try:
            hdr = [str(c) if c is not None else f"col{i}" for i, c in enumerate(next(it))]
        except StopIteration:
            return []
        out = []
        for r in it:
            out.append({h: ("" if v is None else v) for h, v in zip(hdr, r)})
            if len(out) >= max_rows:
                break
        return out
    text = raw.decode("utf-8", "ignore")
    delim = "\t" if name.endswith(".tsv") or text[:2000].count("\t") > text[:2000].count(",") else ","
    return list(csv.DictReader(io.StringIO(text), delimiter=delim))[:max_rows]


def _lower_map(row):
    return {k.strip().lower(): (k, v) for k, v in row.items() if k}


def _pick_col(header_lower, keys):
    for k in keys:
        if k in header_lower:
            return header_lower[k]      # original column name
    return None


def _species_from_text(text):
    t = (text or "").lower()
    for m in _TAXA:
        if m in t:
            return m
    return None


def ingest(file_url, limit=5000):
    """Download one tabular file and extract labelled points. Returns the detected
    mapping + sample so a human/judge can confirm it was interpreted correctly."""
    try:
        rows = _read_table(file_url, limit)
    except Exception as e:
        return {"error": f"read failed: {e}", "file_url": file_url}
    if not rows:
        return {"error": "empty table", "file_url": file_url}
    hl = {k.strip().lower(): k for k in rows[0].keys() if k}
    lat_c = _pick_col(hl, _LAT); lon_c = _pick_col(hl, _LON)
    sp_c = _pick_col(hl, _SPECIES_COLS)
    text_c = next((hl[k] for k in _TEXT_FIELDS if k in hl), None)
    num_vals = [hl[k] for k in hl if any(h in k for h in _VALUE_HINTS)]
    value_field = sp_c or text_c or (num_vals[0] if num_vals else None)
    value_type = ("species" if sp_c else "species(from_text)" if text_c and not sp_c
                  else (num_vals[0] if num_vals else "unknown"))

    pts = []
    for r in rows:
        if not (lat_c and lon_c):
            break
        try:
            lat, lon = float(r[lat_c]), float(r[lon_c])
        except (TypeError, ValueError):
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue
        if sp_c:
            val = r.get(sp_c)
        elif text_c and not sp_c:
            val = _species_from_text(r.get(text_c)) or (r.get(text_c) or "")[:40]
        elif num_vals:
            val = r.get(num_vals[0])
        else:
            val = None
        pts.append({"lat": round(lat, 6), "lon": round(lon, 6), "value": val,
                    "value_type": value_type})
    return {"file_url": file_url, "n_rows": len(rows), "n_points": len(pts),
            "detected": {"lat_col": lat_c, "lon_col": lon_c, "species_col": sp_c,
                         "text_col": text_c, "numeric_value_cols": num_vals,
                         "chosen_value_field": value_field, "value_type": value_type},
            "columns": list(hl.values())[:25], "points": pts, "points_sample": pts[:8],
            "has_coords": bool(lat_c and lon_c), "has_values": bool(value_field),
            "note": "JUDGE: confirm lat/lon + value_field are right. If value is in the "
                    "text_col, species were pulled by keyword — verify a few."}


def _join_key(cols_a, cols_b):
    """A shared, plausibly-unique key column between a value file and a coord file."""
    ka = {c.lower() for c in cols_a}; kb = {c.lower() for c in cols_b}
    for cand in ("point", "point_id", "plot", "plot_id", "site", "site_id", "station",
                 "estate_code", "location", "transect", "id"):
        if cand in ka and cand in kb:
            return cand
    return None


def ingest_dataset(dataset, limit=20000):
    """Dataset-level ingest: handles MULTI-FILE relational data — if a value file lacks
    coordinates, join it to a sibling file that has coords, on a shared key (plot/point/
    site id). This is the 'read the codebook / relational join' hard case."""
    ings = [(f["name"], ingest(f["url"], limit)) for f in dataset.get("files", [])]
    ings = [(n, i) for n, i in ings if not i.get("error")]
    coord_files = [(n, i) for n, i in ings if i.get("has_coords")]
    # direct: any file that already has coords + values
    for n, i in ings:
        if i.get("has_coords") and i.get("has_values") and i["detected"]["value_type"] != "unknown":
            return {"strategy": "single_file", "file": n, **i}
    # relational: value file (no coords) + coord file, joined by key
    for vn, vi in ings:
        if vi.get("has_values") and not vi.get("has_coords"):
            for cn, ci in coord_files:
                if cn == vn:
                    continue
                key = _join_key(vi["columns"], ci["columns"])
                if not key:
                    continue
                # build key -> (lat,lon) from the coord file's raw rows
                crows = _read_table(ci["file_url"], limit)
                kc_c = next((k for k in crows[0] if k.lower() == key), None)
                latc, lonc = ci["detected"]["lat_col"], ci["detected"]["lon_col"]
                coord_by_key = {}
                for r in crows:
                    try:
                        coord_by_key[str(r[kc_c]).strip()] = (float(r[latc]), float(r[lonc]))
                    except (TypeError, ValueError, KeyError):
                        continue
                vrows = _read_table(vi["file_url"], limit)
                kv_c = next((k for k in vrows[0] if k.lower() == key), None)
                valf = vi["detected"]["chosen_value_field"]
                pts = []
                for r in vrows:
                    ll = coord_by_key.get(str(r.get(kv_c, "")).strip())
                    if ll and -90 <= ll[0] <= 90:
                        pts.append({"lat": round(ll[0], 6), "lon": round(ll[1], 6),
                                    "value": r.get(valf), "value_type": vi["detected"]["value_type"]})
                if pts:
                    return {"strategy": "relational_join", "value_file": vn, "coord_file": cn,
                            "join_key": key, "value_type": vi["detected"]["value_type"],
                            "n_points": len(pts), "points": pts, "points_sample": pts[:8],
                            "note": f"JOINED {vn} (values) to {cn} (coords) on '{key}'. JUDGE the join."}
    return {"strategy": "none", "note": "no single file had coords+values and no relational "
            "join found; may need README/codebook reading (a Hermes/trace-mining case).",
            "files": [n for n, _ in ings]}


def search(variable, aoi_bbox, community="ncf", query=None, max_datasets=6):
    """Find + ingest datasets for a variable/species; return points tagged by whether
    they fall in the AOI (best), or near/elsewhere (analog candidate for transfer)."""
    w, s, e, n = [float(x) for x in aoi_bbox]
    got = {"in_aoi": [], "elsewhere": [], "datasets": []}
    v0 = (variable or "").split()[0].lower() if variable else None
    for ds in find(query or variable, community, size=max_datasets):
        ing = ingest_dataset(ds)
        pts = ing.get("points", [])
        if not pts:
            continue
        got["datasets"].append({"title": ds["title"], "doi": ds["doi"], "n_points": len(pts),
                                "value_type": ing.get("value_type") or ing.get("detected", {}).get("value_type"),
                                "strategy": ing.get("strategy")})
        for p in pts:
            if v0 and p.get("value") and v0 not in str(p["value"]).lower():
                continue
            in_aoi = w <= p["lon"] <= e and s <= p["lat"] <= n
            (got["in_aoi"] if in_aoi else got["elsewhere"]).append(
                {**p, "doi": ds["doi"], "aoi_status": "in_aoi" if in_aoi else "near_or_analog"})
    got["counts"] = {k: len(got[k]) for k in ("in_aoi", "elsewhere", "datasets")}
    return got


def inspect(dataset, n_rows=3):
    """The material an LLM needs to semantically match ANY concept to real columns:
    each file's headers + a few rows, plus the whole codebook/README. Works the same
    whether the dataset was pre-crawled or fetched at runtime."""
    out = {"title": dataset.get("title"), "doi": dataset.get("doi"), "files": [], "codebook": ""}
    for f in dataset.get("files", []):
        try:
            raw = _get(f["url"]).decode("utf-8", "ignore")
        except Exception:
            continue
        nm = f["name"].lower()
        if "readme" in nm or "codebook" in nm or nm.endswith(".txt"):
            out["codebook"] += f"\n[{f['name']}]\n" + raw[:4000]
        else:
            lines = raw.splitlines()
            out["files"].append({"name": f["name"], "url": f["url"],
                                 "sample": lines[:n_rows + 1]})
    return out


def extract(file_url, lat_col, lon_col, value_col, value_name="value", limit=20000):
    """Deterministic: pull points once the LLM (or a human) has named the columns."""
    rows = _read_table(file_url, limit)
    hl = {k.strip().lower(): k for k in rows[0].keys() if k} if rows else {}
    lc = hl.get(lat_col.strip().lower(), lat_col)
    oc = hl.get(lon_col.strip().lower(), lon_col)
    vc = hl.get(value_col.strip().lower(), value_col) if value_col else None
    pts = []
    for r in rows:
        try:
            lat, lon = float(r[lc]), float(r[oc])
        except (TypeError, ValueError, KeyError):
            continue
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            pts.append({"lat": round(lat, 6), "lon": round(lon, 6),
                        "value": r.get(vc) if vc else None, "value_type": value_name})
    return pts


def extract_joined(value_url, value_col, coord_url, lat_col, lon_col, join_key,
                   value_name="value", limit=20000):
    """Deterministic relational extract: values in one file, coords in another, joined by
    a key (Point_code/plot/site). THIS is the dominant real-world case for paper datasets."""
    vrows, crows = _read_table(value_url, limit), _read_table(coord_url, limit)
    if not vrows or not crows:
        return []
    ch = {k.strip().lower(): k for k in crows[0] if k}
    kc = ch.get(join_key.lower(), join_key); latc = ch.get(lat_col.lower(), lat_col)
    lonc = ch.get(lon_col.lower(), lon_col)
    # keys are often formatted differently across files (MuP12 vs MuP_plot_2) — index by
    # BOTH the raw key and a normalized (letters, number) form so the join still lands.
    coord = {}
    for r in crows:
        try:
            k = str(r[kc]).strip(); ll = (float(r[latc]), float(r[lonc]))
        except (TypeError, ValueError, KeyError):
            continue
        coord[k] = ll
        nk = _norm_key(k)
        if nk:
            coord.setdefault(nk, ll)
    vh = {k.strip().lower(): k for k in vrows[0] if k}
    kv = vh.get(join_key.lower(), join_key); vc = vh.get(value_col.lower(), value_col)
    pts = []
    for r in vrows:
        raw = str(r.get(kv, "")).strip()
        ll = coord.get(raw) or coord.get(_norm_key(raw))
        if ll and -90 <= ll[0] <= 90 and -180 <= ll[1] <= 180:
            pts.append({"lat": round(ll[0], 6), "lon": round(ll[1], 6),
                        "value": r.get(vc), "value_type": value_name})
    return pts


def _norm_key(k):
    """Normalize a plot/point code to (letters, number): 'MuP12' & 'MuP_plot_12' -> ('mup','12')."""
    m = re.match(r"\s*([A-Za-z]+).*?(\d+)", str(k))
    return (m.group(1).lower() + m.group(2)) if m else None


def _llm_match(material, concept, cli="cursor-agent", timeout=150):
    """Ask an LLM which file+column holds `concept`, from headers+codebook. Returns the
    mapping or None. Pluggable CLI (cursor now; Hermes/122B later). In interactive use,
    Hermes does this in its own reasoning and calls extract() directly instead."""
    import subprocess
    mat = f"CODEBOOK:\n{material['codebook'][:3500]}\n\nFILES:\n"
    for f in material["files"][:8]:
        mat += f"\n[{f['name']}] {(' | '.join(f['sample'][:1]))[:200]}\n  rows: {f['sample'][1:3]}\n"
    prompt = (mat + f"\n\nFor the concept '{concept}', output ONLY JSON "
              '{"present":true|false,"file":"","value_col":"","lat_col":"","lon_col":""}. '
              "Use the codebook to map cryptic column names. lat_col must be the LATITUDE "
              "(~8-30 for India), lon_col the LONGITUDE (~68-98). present=false if absent.")
    for _ in range(3):                       # LLM match is non-deterministic -> retry
        try:
            if cli not in ("cursor-agent", "cursor"):
                return None
            p = subprocess.run(["cursor-agent", "-p", "--output-format", "text", "--trust", prompt],
                               capture_output=True, text=True, timeout=timeout)
            m = re.search(r"\{.*\}", p.stdout, re.DOTALL)
            if m:
                d = json.loads(m.group(0))
                if d.get("present") and d.get("file") and d.get("lat_col"):
                    return d
        except Exception:
            continue
    return None


_INDIA = (68.0, 6.0, 98.0, 37.0)   # sanity box to catch swapped/wrong coord columns


def _sane_fraction(pts):
    if not pts:
        return 0.0
    w, s, e, n = _INDIA
    return sum(1 for p in pts if w <= p["lon"] <= e and s <= p["lat"] <= n) / len(pts)


def concept_search(concept, aoi_bbox, datasets=None, community="ncf", cli="cursor-agent",
                   max_datasets=6):
    """LLM-driven search for ANY concept across a corpus of paper datasets. For each
    dataset: inspect -> LLM matches concept to the real column -> extract points.
    `datasets` can be a pre-crawled list or None (then it finds them). Corpus-agnostic:
    identical logic whether pre-downloaded or fetched at runtime."""
    w, s, e, n = [float(x) for x in aoi_bbox]
    dss = datasets or find(concept, community, size=max_datasets)
    got = {"concept": concept, "in_aoi": [], "elsewhere": [], "matched_datasets": []}
    for ds in dss[:max_datasets]:
        mat = inspect(ds)
        if not mat["files"]:
            continue
        mp = _llm_match(mat, concept, cli)
        if not mp:
            continue
        fu = next((f["url"] for f in mat["files"] if f["name"] == mp["file"]), None)
        if not fu:
            continue
        pts = extract(fu, mp["lat_col"], mp["lon_col"], mp.get("value_col"), concept)
        if _sane_fraction(pts) < 0.5:        # guardrail: LLM may swap lat/lon -> try swap
            pts_sw = extract(fu, mp["lon_col"], mp["lat_col"], mp.get("value_col"), concept)
            pts = pts_sw if _sane_fraction(pts_sw) > _sane_fraction(pts) else pts
        if not pts or _sane_fraction(pts) < 0.5:   # can't validate -> don't trust it
            continue
        got["matched_datasets"].append({"title": ds["title"], "doi": ds["doi"],
                                        "file": mp["file"], "column": mp.get("value_col"),
                                        "n_points": len(pts)})
        for p in pts:
            in_aoi = w <= p["lon"] <= e and s <= p["lat"] <= n
            (got["in_aoi"] if in_aoi else got["elsewhere"]).append({**p, "doi": ds["doi"]})
    got["counts"] = {k: len(got[k]) for k in ("in_aoi", "elsewhere", "matched_datasets")}
    return got


def describe():
    return {
        "connector": "paper_data",
        "purpose": "Ingest datasets/codebooks inside research papers (Zenodo/Dryad) — "
                   "presence points, plot/soil/trait values — and return them like GBIF.",
        "functions": [
            "find(query|community='ncf') -> datasets with tabular files",
            "ingest(file_url) -> detected coords + value + extracted points (verify!)",
            "search(variable, aoi_bbox) -> points tagged in_aoi | near_or_elsewhere",
        ],
        "communities": COMMUNITIES,
        "use": "get the non-GBIF stuff (soil, plots, traits) from papers; feed nearby/analog "
               "points into predict(regress) or interpolate to estimate values at your AOI.",
        "gotcha": "column names and value fields vary wildly; the species is often in a "
                  "free-text field. ALWAYS have a human/judge confirm the ingest mapping. "
                  "Coordinates can be imprecise (field GPS) — ground-truth matters.",
    }


def _main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="paper_data")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    fp = sub.add_parser("find"); fp.add_argument("--query"); fp.add_argument("--community", default="ncf")
    ig = sub.add_parser("ingest"); ig.add_argument("--url", required=True)
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    if args.cmd == "find":
        try:
            print(json.dumps(find(args.query, args.community), indent=2)[:4000])
        except Exception as e:                       # transient API/network error → clean message, not a traceback
            print(json.dumps({"query": args.query, "error": str(e)[:140],
                              "hint": "likely a transient Zenodo/API error — retry once with a SHORT 1-3 word "
                                      "query (e.g. 'snake' or 'reptile'), or move on and note the gap."}, indent=2))
    elif args.cmd == "ingest":
        print(json.dumps(ingest(args.url), indent=2))


if __name__ == "__main__":
    _main()
