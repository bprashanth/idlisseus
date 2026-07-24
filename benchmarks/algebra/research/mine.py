"""mine.py — consult real research + extract indicators/questions.

Two real sources (no fabrication, provenance-stamped):
  - OpenAlex  (scholarly literature, free, no key) -> papers + abstracts
  - Zenodo    (datasets + codebooks) -> attached CSV/data files

Indicator/question extraction uses the cursor-agent CLI (headless `-p`) as the
frontier reasoner, since it's the available cloud model. Kept single-shot + tight
so each call is cheap and fast. Everything returns a provenance stamp.
"""
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

OPENALEX = "https://api.openalex.org/works"
ZENODO = "https://zenodo.org/api/records"
MAILTO = "prashanthseven@gmail.com"   # OpenAlex polite pool

_last_call = [0.0]
_MIN_INTERVAL = 1.3   # seconds between external calls (be polite; avoid 429)


def _get(url, timeout=30, tries=2):
    """Throttled GET with one 429/5xx backoff, then raise (caller fails over)."""
    for attempt in range(tries):
        wait = _MIN_INTERVAL - (time.time() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.time()
        req = urllib.request.Request(url, headers={"User-Agent": "idlisseus-research/0.1 (mailto:%s)" % MAILTO})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < tries - 1:
                time.sleep(4)
                continue
            raise


def _stamp(url):
    return {"source_url": url,
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "license": "unknown"}


def _deinvert(inv):
    """OpenAlex abstract_inverted_index -> plain text."""
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))[:2500]


def openalex_papers(query, per_page=4, since_year=2010):
    url = (f"{OPENALEX}?search={urllib.parse.quote(query)}"
           f"&filter=from_publication_date:{since_year}-01-01"
           f"&per-page={per_page}&mailto={MAILTO}")
    out = []
    for w in _get(url).get("results", []):
        out.append({
            "title": w.get("title"), "doi": w.get("doi"),
            "year": w.get("publication_year"),
            "abstract": _deinvert(w.get("abstract_inverted_index")),
            "oa_url": (w.get("open_access") or {}).get("oa_url"),
            "cited_by": w.get("cited_by_count"),
            "provenance": _stamp(w.get("id") or url)})
    return out


EUROPEPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
CROSSREF = "https://api.crossref.org/works"
_COOLDOWN = {}          # source name -> epoch until which to skip it (after a 429)


def _cool(src):
    _COOLDOWN[src] = time.time() + 1200      # rest a throttled source for 20 min


def _cooling(src):
    return time.time() < _COOLDOWN.get(src, 0)


def europepmc_papers(query, per_page=3, since_year=2005):
    url = f"{EUROPEPMC}?" + urllib.parse.urlencode(
        {"query": query, "format": "json", "pageSize": per_page, "resultType": "core"})
    out = []
    for r in _get(url).get("resultList", {}).get("result", []):
        doi = r.get("doi")
        yr = r.get("pubYear", "")
        out.append({"title": r.get("title"),
                    "doi": ("https://doi.org/" + doi) if doi else ("EPMC:" + str(r.get("id"))),
                    "year": int(yr) if str(yr).isdigit() else None,
                    "abstract": (r.get("abstractText") or "")[:2500],
                    "oa_url": None, "source": "EuropePMC", "provenance": _stamp(url)})
    return out


def crossref_papers(query, per_page=3):
    url = f"{CROSSREF}?" + urllib.parse.urlencode({"query": query, "rows": per_page, "mailto": MAILTO})
    out = []
    for r in _get(url).get("message", {}).get("items", []):
        doi = r.get("DOI")
        out.append({"title": (r.get("title") or [""])[0],
                    "doi": ("https://doi.org/" + doi) if doi else None,
                    "year": (r.get("published", {}).get("date-parts", [[None]])[0][0]),
                    "abstract": re.sub(r"<[^>]+>", "", r.get("abstract", "") or "")[:2500],
                    "oa_url": None, "source": "Crossref", "provenance": _stamp(url)})
    return out


S2 = "https://api.semanticscholar.org/graph/v1/paper/search"


def semanticscholar_papers(query, per_page=3):
    url = f"{S2}?" + urllib.parse.urlencode(
        {"query": query, "fields": "title,abstract,year,externalIds", "limit": per_page})
    out = []
    for p in (_get(url).get("data") or []):
        doi = (p.get("externalIds") or {}).get("DOI")
        out.append({"title": p.get("title"),
                    "doi": ("https://doi.org/" + doi) if doi else ("S2:" + str(p.get("paperId"))),
                    "year": p.get("year"), "abstract": (p.get("abstract") or "")[:2500],
                    "oa_url": None, "source": "SemanticScholar", "provenance": _stamp(url)})
    return out


# EuropePMC first (abstracts, reliable); S2/OpenAlex/Crossref as failovers.
_SOURCES = [("europepmc", europepmc_papers), ("semanticscholar", semanticscholar_papers),
            ("openalex", openalex_papers), ("crossref", crossref_papers)]


def zenodo_org_data(org, size=3):
    """Zenodo DATASETS from a specific org (NCF/ATREE/Keystone...) — capture their
    real CSV/codebook files (the 'look inside paper CSVs' the broker wants)."""
    url = f"{ZENODO}?" + urllib.parse.urlencode({"q": f'"{org}"', "type": "dataset", "size": size})
    out = []
    for h in _get(url).get("hits", {}).get("hits", []):
        files = [{"name": f.get("key"), "size_mb": round(f.get("size", 0) / 1e6, 2),
                  "url": f.get("links", {}).get("self")}
                 for f in h.get("files", [])
                 if str(f.get("key", "")).lower().endswith((".csv", ".xlsx", ".tsv", ".txt"))]
        out.append({"title": h.get("metadata", {}).get("title"), "doi": h.get("doi"),
                    "org": org, "data_files": files,
                    "provenance": _stamp(h.get("links", {}).get("self_html"))})
    return out


def unpaywall_oa(doi, email=MAILTO):
    """Legal open-access full-text locator (used instead of piracy sources)."""
    doi = (doi or "").replace("https://doi.org/", "")
    if not doi or doi.startswith(("S2:", "EPMC:")):
        return {"is_oa": None}
    try:
        d = _get(f"https://api.unpaywall.org/v2/{doi}?email={email}")
        return {"is_oa": d.get("is_oa"), "url": (d.get("best_oa_location") or {}).get("url")}
    except Exception:
        return {"is_oa": None}


def search_papers(query, per_page=3):
    """Try literature sources in order, skipping any in cooldown; fail over on 429.
    EuropePMC first (has abstracts, not blocked); OpenAlex/Crossref as backups."""
    last_err = None
    for name, fn in _SOURCES:
        if _cooling(name):
            continue
        try:
            r = fn(query, per_page)
            if r:
                return r
        except urllib.error.HTTPError as e:
            last_err = f"{name}:{e.code}"
            if e.code in (429, 403):
                _cool(name)
        except Exception as e:
            last_err = f"{name}:{type(e).__name__}"
    if last_err:
        raise RuntimeError(last_err)
    return []


def zenodo_datasets(query, size=4):
    toks = re.findall(r"[A-Za-z]{4,}", query)
    q = " AND ".join(toks) if toks else query
    url = f"{ZENODO}?" + urllib.parse.urlencode({"q": q, "type": "dataset", "size": size})
    out = []
    for h in _get(url).get("hits", {}).get("hits", []):
        files = [{"name": f.get("key"), "size_mb": round(f.get("size", 0) / 1e6, 2),
                  "url": f.get("links", {}).get("self")}
                 for f in h.get("files", [])
                 if str(f.get("key", "")).lower().endswith((".csv", ".xlsx", ".txt", ".tsv"))]
        out.append({"title": h.get("metadata", {}).get("title"), "doi": h.get("doi"),
                    "data_files": files, "provenance": _stamp(h.get("links", {}).get("self_html"))})
    return out


_EXTRACT_PROMPT = (
    "You are extracting measurable ecological indicators from a research abstract "
    "for a dry-deciduous forest restoration site (Krishnagiri, S. India). "
    "Output ONLY a compact JSON array (no prose, no markdown fences). Each element: "
    '{"indicator": "...", "question": "a question a restoration team would ask", '
    '"unit": "...", "measurable_via": "one of: satellite_timeseries | species_occurrence | '
    'bird_trend_dataset | field_survey | socioeconomic_dataset | unknown"}. '
    "Max 4 elements, only genuinely measurable indicators. Abstract:\n\n")


def extract_indicators(text, timeout=150):
    """Call cursor-agent headless to extract indicators. Returns [] on failure."""
    if not text or len(text) < 40:
        return []
    try:
        p = subprocess.run(
            ["cursor-agent", "-p", "--output-format", "text", "--trust",
             _EXTRACT_PROMPT + text[:2200]],
            capture_output=True, text=True, timeout=timeout)
        out = p.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    m = re.search(r"\[.*\]", out, re.DOTALL)
    if not m:
        return []
    try:
        arr = json.loads(m.group(0))
        return [a for a in arr if isinstance(a, dict) and a.get("indicator")][:4]
    except json.JSONDecodeError:
        return []


# free fallback when cursor-agent is capped / quota-exhausted: keyword -> indicator.
_HEUR = [
    (("ndvi", "greenness", "canopy", "cover", "vegetation", "biomass", "carbon"),
     "satellite_timeseries", "vegetation/greenness"),
    (("rainfall", "precipitation", "drought", "climate", "monsoon"),
     "satellite_timeseries", "rainfall/climate"),
    (("occurrence", "species richness", "diversity", "abundance", "invasion", "invasive", "lantana"),
     "species_occurrence", "species occurrence"),
    (("bird", "avifauna", "avian"), "bird_trend_dataset", "bird trend"),
    (("income", "livelihood", "employment", "wage", "household", "socioeconomic"),
     "socioeconomic_dataset", "livelihoods"),
    (("survival", "seedling", "sapling", "nursery", "planting", "soil", "growth"),
     "field_survey", "field measurement"),
]


def heuristic_indicators(text):
    """Regex/keyword indicator extraction — free, used when cursor is unavailable."""
    tl = (text or "").lower()
    out, seen = [], set()
    for keys, via, label in _HEUR:
        hit = next((k for k in keys if k in tl), None)
        if hit and via not in seen:
            seen.add(via)
            out.append({"indicator": f"{label} ({hit})",
                        "question": f"What does the data say about {label} at the site?",
                        "unit": "varies", "measurable_via": via})
    return out[:4]
