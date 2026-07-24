#!/usr/bin/env python3
"""autoloop.py — long-running, checkpointing, resumable research broker.

Runs for hours: mine papers -> extract indicators -> measure against real data
(GBIF/SoIB/EE connectors incl. AlphaEarth embeddings) -> index to KB -> snowball
(species/keywords from papers become new queries) -> periodically ask cursor (as an
independent judge) for a narrative + clarifying questions, then try to answer them.

Safety for unattended running:
  * CHECKPOINT every paper to state.json (+ append-only kb.jsonl). Resumable: re-run
    with the same --state and it skips seen DOIs and continues.
  * CURSOR CAP + FREE FALLBACK: cursor-agent is paid/quota-limited. Capped by
    --max-cursor; if the cap is hit or cursor fails repeatedly, extraction falls back
    to a free heuristic and the loop keeps going (data-only). Resume with more quota
    later — seen DOIs are skipped, cursor budget resets by editing state.
  * DISK GUARD: if free disk < --disk-min-gb, sync research/cache + kb to s3://idlisseus
    and prune local cache. (aws cli required.)
  * BUDGET: stops cleanly at --budget-seconds; everything is checkpointed.

  python3 research/autoloop.py --budget-seconds 39600 --max-cursor 60
  python3 research/autoloop.py --resume          # pick up from the checkpoint
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ALGEBRA = os.path.dirname(HERE)
SB = os.path.abspath(os.path.join(ALGEBRA, "..", "semantic_broker"))
CACHE = os.path.join(HERE, "cache")
STATE = os.path.join(HERE, "state.json")
NARR = os.path.join(HERE, "narratives.jsonl")
S3 = "s3://idlisseus"
DISK_MIN = 10.0   # GB; overridden by --disk-min-gb
PRIORITY_ORGS = []   # Rainmatter fundees + ERA India members (loaded from cursor_sources.json)
SEARCH_TERMS = []    # curated Indian org/author query strings
sys.path.insert(0, HERE)
import mine, measure, kb  # noqa: E402

AOIS = [os.path.join(ALGEBRA, "aois", a) for a in
        ("elephants_by_the_lake.json", "anamalai_nilgiris.json",
         "kanha_central_india.json", "aravalli_fes.json", "meghalaya_groves.json")]
THEMES = ["invasives", "restoration", "biodiversity", "water", "elephants",
          "livelihoods", "nurseries"]
# curated ecological topics — a large clean query space (topic x ecoregion x year x org)
# so the loop keeps surfacing genuinely new literature for hours.
ECO_TOPICS = [
    "seed dispersal", "pollination", "soil carbon", "mycorrhiza", "leaf phenology",
    "fire regime", "grazing pressure", "non-timber forest products", "agroforestry",
    "groundwater recharge", "spring hydrology", "canopy cover", "natural regeneration",
    "assisted natural regeneration", "invasive species removal", "native tree survival",
    "frugivory", "seed predation", "dung beetle diversity", "butterfly diversity",
    "odonate dragonfly", "bird community", "amphibian diversity", "reptile survey",
    "mammal camera trap", "elephant movement corridor", "human elephant conflict",
    "crop raiding", "dry season water stress", "drought resilience", "carbon sequestration",
    "above ground biomass", "species distribution model", "habitat connectivity",
    "edge effect", "forest fragmentation", "litter decomposition", "nutrient cycling",
    "water quality", "fodder grass", "fuelwood", "wild honey", "ethnobotany",
    "tribal forest livelihood", "restoration economics", "seedling nursery survival",
    "tank irrigation", "millet farming", "sacred grove", "lantana management",
]
THEME_Q = mine.__dict__.get("THEME_QUERIES", {})  # not used; queries built below


# ---------- checkpoint ----------
def load_state():
    s = json.load(open(STATE)) if os.path.exists(STATE) else {}
    s.setdefault("seen_dois", []); s.setdefault("cursor_calls", 0)
    s.setdefault("cursor_fails", 0); s.setdefault("cursor_dead", False)
    s.setdefault("cursor_next", 0); s.setdefault("ran_queries", [])
    s.setdefault("queue", []); s.setdefault("sat", {})
    for k in ("n_papers", "n_ind", "n_measured", "n_gap"):
        s.setdefault(k, 0)
    s.setdefault("started", time.strftime("%Y-%m-%dT%H:%M:%S"))
    return s


def cursor_ok(state):
    """Paced + hard-capped, persistent across resumes: <=1 call / 6 min, <= max_cursor total."""
    return (not state["cursor_dead"] and state["cursor_calls"] < state.get("max_cursor", 150)
            and time.time() >= state.get("cursor_next", 0))


def cursor_used(state):
    state["cursor_calls"] += 1
    state["cursor_next"] = time.time() + 360   # >= 6 min until the next cursor call


def save_state(s):
    tmp = STATE + ".tmp"
    json.dump(s, open(tmp, "w"), indent=1)
    os.replace(tmp, STATE)


# ---------- resources ----------
def disk_free_gb():
    return shutil.disk_usage("/").free / 1e9


def disk_guard():
    if disk_free_gb() >= DISK_MIN:
        return
    os.makedirs(CACHE, exist_ok=True)
    subprocess.run(["aws", "s3", "mb", S3], capture_output=True)  # no-op if exists
    subprocess.run(["aws", "s3", "sync", CACHE, f"{S3}/cache"], capture_output=True)
    subprocess.run(["aws", "s3", "cp", kb.KB, f"{S3}/kb.jsonl"], capture_output=True)
    for f in glob.glob(os.path.join(CACHE, "*")):
        try:
            os.remove(f)
        except OSError:
            pass
    log(f"[disk] low ({disk_free_gb():.1f}G); offloaded cache+kb to {S3}")


# ---------- cursor (bounded frontier) ----------
def cursor(prompt, timeout=150):
    try:
        p = subprocess.run(["cursor-agent", "-p", "--output-format", "text", "--trust", prompt],
                           capture_output=True, text=True, timeout=timeout)
        return p.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def extract(text, state):
    """Paced cursor extraction; else free heuristic. Marks cursor dead after 3 fails."""
    if cursor_ok(state):
        r = mine.extract_indicators(text)
        cursor_used(state)
        if r:
            state["cursor_fails"] = 0
            return r, "cursor"
        state["cursor_fails"] += 1
        if state["cursor_fails"] >= 3:      # transient? pause, don't kill — self-recovers
            state["cursor_fails"] = 0
            state["cursor_next"] = time.time() + 1800   # rest cursor 30 min, then retry
            log("[cursor] 3 empty calls -> pausing cursor 30min (heuristic meanwhile)")
    return mine.heuristic_indicators(text), "heuristic"


# ---------- satellite + embedding intersect ----------
def compute_sat(aoi):
    """One-time per AOI: satellite trend + embedding convergence + EMIT hyperspectral
    + a MODELLED invasive-presence (predict RF on embeddings) for hypothesis corroboration."""
    lat, lon = aoi["center"]
    ref = aoi.get("reference_forest") or [lat, lon]
    bbox = ",".join(str(x) for x in (aoi.get("corridor_bbox") or aoi["bbox"]))  # wider = more training pts
    inv = next((s for s in aoi.get("seed_species", [])
                if any(m in s.lower() for m in ("lantana", "prosopis", "parthenium",
                                                "chromolaena", "juliflora"))), "Lantana camara")
    script = f"""
import ee,sys,json; ee.Initialize(project='plantwars'); sys.path.insert(0,'/opt/data')
from connectors.greenness import trend
from connectors.fire import exposure
from connectors.landcover import classify
from connectors.embedding import similarity_trend
from connectors.occurrence import search
from connectors.predict import presence
from connectors.hyperspectral import indices as hyp
p=[{{'id':'c','lat':{lat},'lon':{lon}}}]
g=trend(p,years='2019-2025')[0]; f=exposure(p,radius_km=5,years='2020-2025')[0]
l=classify(p)[0]; e=similarity_trend(p,[{ref[0]},{ref[1]}],years='2019-2024')[0]
try: hy=hyp(p)[0]
except Exception: hy={{}}
inv='{inv}'; bbox=[{bbox}]
try:
    pts=search(inv, bbox, limit=150)
    pr=presence(pts, bbox, year=2023) if len(pts)>=10 else {{'note':'too few occ pts ('+str(len(pts))+')'}}
except Exception as ex: pr={{'error':str(ex)[:80]}}
print(json.dumps({{'ndvi_trend':g['trend_class'],'ndvi_slope':g['ndvi_slope'],
 'fire_5km_5yr':f['fire_count'],'landcover':l['landcover'],
 'embed_converging':e['converging'],'embed_sim_end':e['sim_end'],
 'hyp_ndvi':hy.get('ndvi_hyp'),'hyp_rededge':hy.get('rededge'),'hyp_cai':hy.get('cai'),
 'invasive':inv,'invasive_present_fraction':pr.get('modelled_present_fraction'),
 'invasive_model_accuracy':pr.get('test_accuracy'),'invasive_note':pr.get('note') or pr.get('error'),
 'source':'MODIS/WorldCover/AlphaEarth/EMIT/RF-predict'}}))
"""
    sp = os.path.join(CACHE, "sat_tmp.py")
    os.makedirs(CACHE, exist_ok=True)
    open(sp, "w").write(script)
    try:
        p = subprocess.run(
            ["docker", "run", "--rm", "--network", "host",
             "-v", f"{os.path.expanduser('~')}/.hermes:/opt/data",
             "-v", f"{os.path.join(SB, 'connectors')}:/opt/data/connectors:ro",
             "-v", f"{sp}:/opt/data/sat_tmp.py:ro", "-e", "HOME=/opt/data", "-w", "/opt/data",
             "--entrypoint", "/opt/hermes/.venv/bin/python3", "hermes-agent-local",
             "/opt/data/sat_tmp.py"], capture_output=True, text=True, timeout=600)
        return json.loads(p.stdout[p.stdout.index("{"):p.stdout.rindex("}") + 1])
    except Exception as ex:
        return {"error": str(ex)[:120]}


# ---------- snowball ----------
_STOP = {"the", "and", "for", "with", "from", "this", "that", "study", "forest", "india",
         "species", "using", "based", "data", "results", "which", "were", "have"}


_NOT_GENUS = {"the", "this", "that", "these", "those", "india", "indian", "asian", "its",
              "our", "their", "we", "molecular", "land", "forest", "using", "results",
              "study", "here", "among", "both", "however", "during", "based", "within",
              "new", "two", "three", "first", "most", "many", "several", "recent",
              "present", "total", "high", "low", "large", "small", "south", "north",
              "eastern", "western", "central", "global", "climate", "human", "wild"}


def snowball(paper, aoi):
    """Disabled: extracting binomials from arbitrary abstracts was too noisy
    ('Cistercian monasteries'). We snowball instead from REAL measured species in
    the KB (see replenish -> kb_species), which is clean and grounded."""
    return []


# ---------- hypothesis (cursor as judge) ----------
def load_priority():
    """Rainmatter fundees + ERA India members + curated search strings (from the
    cursor consult). EBTL is a Rainmatter project, so co-fundees (NCF/ATREE/Keystone/
    FES/Dakshin...) are the high-quality-data orgs to prioritize."""
    global PRIORITY_ORGS, SEARCH_TERMS
    f = os.path.join(HERE, "cursor_sources.json")
    if os.path.exists(f):
        d = json.load(open(f))
        PRIORITY_ORGS = list(dict.fromkeys(d.get("rainmatter_fundees", [])
                                           + d.get("era_india_members", [])))
        SEARCH_TERMS = d.get("search_terms", [])


def priority_jobs(aois, ran):
    """Indian-source-first jobs: curated author/org strings + fundee x theme."""
    jobs, seen = [], set()
    ebtl = aois[0]["name"]
    for t in SEARCH_TERMS:                       # already specific (place/author/topic)
        if t not in ran and t not in seen:
            seen.add(t); jobs.append({"aoi": ebtl, "theme": "india_priority", "q": t})
    for aoi in aois:
        for org in PRIORITY_ORGS:
            for th in ("restoration", "biodiversity", "livelihoods", "human elephant conflict"):
                q = f"{org} {th} India"
                if q not in ran and q not in seen:
                    seen.add(q); jobs.append({"aoi": aoi["name"], "theme": "fundee", "q": q})
    return jobs


def mine_org_data(state):
    """One-time: index the priority orgs' real Zenodo DATASETS + their CSV/codebook
    files (NCF Valparai mammal records, etc.) — the 'look inside the CSVs' step."""
    if state.get("org_data_done"):
        return
    n = 0
    for org in PRIORITY_ORGS:
        try:
            ds = mine.zenodo_org_data(org, size=3)
        except Exception:
            continue
        for d in ds:
            if not d.get("doi"):
                continue
            kb.append({"aoi": "all", "theme": "org_dataset",
                       "paper": {"title": d["title"], "doi": d["doi"], "year": None},
                       "indicator": {"indicator": f"dataset published by {org}",
                                     "measurable_via": "dataset"},
                       "result": {"org": org, "n_data_files": len(d["data_files"]),
                                  "data_files": d["data_files"][:5], "source": "Zenodo"},
                       "extractor": "zenodo_org",
                       "status": "measured" if d["data_files"] else "gap",
                       "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
            n += 1
    state["org_data_done"] = True
    log(f"[org_data] indexed {n} priority-org datasets from Zenodo")


def replenish(state, aois):
    """Never run dry: Indian-priority jobs first, then KB species + AOI taxa +
    themes + analog sites. As the KB grows, this keeps yielding new angles."""
    ran = set(state["ran_queries"])
    kb_species = {r["result"].get("species_used") for r in kb.load()
                  if r.get("result", {}).get("species_used")}
    mods = ["ecology", "impact", "monitoring", "distribution", "population trend",
            "climate change", "restoration", "management"]
    new, seen = [], set()
    years = ["2024", "2023", "2022", "2021", "2020", "2019", "2018", "2016"]
    for aoi in aois:
        eco = aoi.get("ecoregion", "")
        taxa = (aoi.get("seed_species", []) + aoi.get("native_trees", [])
                + aoi.get("flagship_birds", []) + [s for s in kb_species if s])
        for sp in taxa:
            for m in mods[:3]:
                q = f"{sp} {m} India"
                if q not in ran and q not in seen:
                    seen.add(q); new.append({"aoi": aoi["name"], "theme": "snowball", "q": q})
        for site in aoi.get("analog_sites", []):
            q = f"{site['name']} biodiversity restoration"
            if q not in ran and q not in seen:
                seen.add(q); new.append({"aoi": aoi["name"], "theme": "analog", "q": q})
        # large curated topic space (topic x ecoregion x year, and topic x priority org)
        # so the loop keeps finding genuinely new literature for hours, not sentence junk.
        for tp in ECO_TOPICS:
            q = f"{tp} {eco} India"
            if q not in ran and q not in seen:
                seen.add(q); new.append({"aoi": aoi["name"], "theme": "topic", "q": q})
            for yr in years:
                q = f"{tp} dry deciduous forest India {yr}"
                if q not in ran and q not in seen:
                    seen.add(q); new.append({"aoi": aoi["name"], "theme": "topic", "q": q})
            for org in PRIORITY_ORGS[:6]:
                q = f"{org} {tp}"
                if q not in ran and q not in seen:
                    seen.add(q); new.append({"aoi": aoi["name"], "theme": "fundee_topic", "q": q})
        for th in THEMES:
            for m in mods:
                q = f"{th} {eco} {m} India"
                if q not in ran and q not in seen:
                    seen.add(q); new.append({"aoi": aoi["name"], "theme": th, "q": q})
    return (priority_jobs(aois, ran) + new)[:150]   # Indian-priority jobs first


def refresh_measure(aois, state):
    """When no new papers exist, keep producing signal: re-measure AOI species
    occurrence-over-time (real; the 'is X showing up' question, tracked through time)."""
    for aoi in aois:
        for sp in aoi.get("seed_species", [])[:4]:
            r = measure.gbif_by_year(sp, [float(x) for x in aoi["bbox"]])
            kb.append({"aoi": aoi["name"], "theme": "monitoring", "paper": None,
                       "indicator": {"indicator": f"{sp} occurrence over time",
                                     "measurable_via": "species_occurrence"},
                       "result": {**r, "species_used": sp}, "extractor": "refresh",
                       "status": "measured" if r.get("measured") else "gap",
                       "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
    log("[refresh] re-measured AOI species occurrence trends")


def discover_species(aois, state):
    """Idle-time 'keep looking': catalog each AOI's top GBIF species + their
    occurrence trend, tracking what's been done so it saturates cleanly. Returns
    how many NEW species were catalogued this pass."""
    measured = set(state.setdefault("measured_species", []))
    added = 0
    for aoi in aois:
        for sp in measure.gbif_top_species([float(x) for x in aoi["bbox"]], 15):
            key = aoi["name"] + "|" + sp
            if key in measured:
                continue
            measured.add(key)
            r = measure.gbif_by_year(sp, [float(x) for x in aoi["bbox"]])
            kb.append({"aoi": aoi["name"], "theme": "species_catalog", "paper": None,
                       "indicator": {"indicator": f"{sp} occurrence trend",
                                     "measurable_via": "species_occurrence"},
                       "result": {**r, "species_used": sp}, "extractor": "discover",
                       "status": "measured" if r.get("measured") else "gap",
                       "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
            added += 1
            if added >= 10:      # bounded per idle cycle
                break
        if added >= 10:
            break
    state["measured_species"] = list(measured)
    if added:
        log(f"[discover] catalogued {added} new species occurrence trends")
    return added


def hypothesis(aoi, theme, sat, state):
    if not cursor_ok(state):
        return
    slice_ = [r for r in kb.load() if r.get("aoi") == aoi["name"] and r.get("theme") == theme][-8:]
    if len(slice_) < 2:
        return
    facts = json.dumps({"aoi": aoi["label"], "satellite": sat,
                        "indicators": [{"i": r["indicator"]["indicator"],
                                        "r": r["result"].get("trend") or r["status"]}
                                       for r in slice_]})[:1800]
    prompt = ("Given these real indicator readings for a forest-restoration site, output ONLY "
              "compact JSON {\"narrative\":\"one plausible explanation of what's happening\","
              "\"clarifying_questions\":[\"q1\",\"q2\"]}. Readings:\n" + facts)
    out = cursor(prompt)
    cursor_used(state)
    if not out:
        return
    m = re.search(r"\{.*\}", out, re.DOTALL)
    if m:
        try:
            rec = json.loads(m.group(0))
            rec.update({"aoi": aoi["name"], "theme": theme, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
            open(NARR, "a").write(json.dumps(rec) + "\n")
            log(f"[hypothesis:{aoi['name']}/{theme}] {rec.get('narrative','')[:90]}")
        except json.JSONDecodeError:
            pass


# ---------- logging ----------
_LOG = os.path.join(HERE, "autoloop.log")


def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    open(_LOG, "a").write(line + "\n")


def run(budget_s, max_cursor):
    state = load_state()
    state["max_cursor"] = max_cursor
    state["run_start"] = time.time()
    load_priority()
    state["queue"] = [j for j in state["queue"] if j.get("theme") != "snowball"]  # purge junk
    aois = [json.load(open(a)) for a in AOIS]
    for aoi in aois:                        # compute satellite+embedding+ML once per AOI
        if aoi["name"] not in state["sat"]:
            sat = compute_sat(aoi)
            state["sat"][aoi["name"]] = sat
            log(f"[sat:{aoi['name']}] {sat}")
            if sat.get("invasive_present_fraction") is not None:   # modelled corroboration -> KB
                kb.append({"aoi": aoi["name"], "theme": "corroboration", "paper": None,
                           "indicator": {"indicator": f"modelled presence of {sat.get('invasive')}",
                                         "measurable_via": "ml_predict"},
                           "result": {"present_fraction": sat.get("invasive_present_fraction"),
                                      "model_accuracy": sat.get("invasive_model_accuracy"),
                                      "embed_converging": sat.get("embed_converging"),
                                      "hyp_rededge": sat.get("hyp_rededge"),
                                      "source": "predict RF on AlphaEarth + EMIT", "modelled": True},
                           "extractor": "predict", "status": "measured",
                           "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
            save_state(state)
    mine_org_data(state); save_state(state)   # index NCF/ATREE/... Zenodo datasets once
    if not state["queue"]:
        for aoi in aois:
            for th in THEMES:
                state["queue"].append({"aoi": aoi["name"], "theme": th,
                                       "q": f"{th} {aoi['ecoregion']} restoration India"})
    # Indian-priority (Rainmatter fundee / curated) jobs go to the FRONT of the queue
    have = {j["q"] for j in state["queue"]}
    state["queue"] = [j for j in priority_jobs(aois, set(state["ran_queries"]))
                      if j["q"] not in have] + state["queue"]
    save_state(state)

    aoi_by = {a["name"]: a for a in aois}
    start = time.time()
    idle = 0
    while time.time() - start < budget_s:            # only the budget stops us
        if not state["queue"]:                        # never run dry
            state["queue"] += replenish(state, aois)
            save_state(state)
            if not state["queue"]:
                n_disc = discover_species(aois, state)   # keep looking: species catalog + trends
                refresh_measure(aois, state); save_state(state)
                idle = 0 if n_disc else idle + 1
                log(f"[idle #{idle}] queue empty; discovered {n_disc} species, refreshed; sleeping")
                time.sleep(120 if idle < 8 else 900)
                continue
        idle = 0
        job = state["queue"].pop(0)
        state["ran_queries"].append(job["q"])
        aoi = aoi_by[job["aoi"]]
        sat = state["sat"].get(aoi["name"], {})
        try:
            papers = mine.search_papers(job["q"], per_page=3)
        except Exception as ex:
            log(f"[mine] {job['q'][:40]}: {ex}"); save_state(state); time.sleep(3); continue
        new = [p for p in papers if p.get("doi") and p["doi"] not in state["seen_dois"]]
        log(f"[{aoi['name']}/{job['theme']}] q={job['q'][:44]!r}: {len(new)} new "
            f"(cursor {state['cursor_calls']}/{max_cursor}, q{len(state['queue'])}, "
            f"disk {disk_free_gb():.0f}G, {(time.time()-start)/3600:.1f}h)")
        for p in new:
            state["seen_dois"].append(p["doi"]); state["n_papers"] += 1
            inds, how = extract(p["abstract"], state)
            for ind in inds:
                res = measure.measure(ind, aoi, sat)
                gap = bool(res.get("gap"))
                state["n_gap"] += gap; state["n_measured"] += (not gap); state["n_ind"] += 1
                kb.append({"aoi": aoi["name"], "theme": job["theme"],
                           "paper": {"title": p["title"], "doi": p["doi"], "year": p["year"]},
                           "indicator": ind, "result": res, "extractor": how,
                           "status": "gap" if gap else "measured",
                           "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
            for nq in snowball(p, aoi):
                if nq not in state["ran_queries"] and not any(j["q"] == nq for j in state["queue"]):
                    state["queue"].append({"aoi": aoi["name"], "theme": job["theme"], "q": nq})
            save_state(state)
            disk_guard()
        hypothesis(aoi, job["theme"], sat, state)
        save_state(state)

    save_state(state)
    log(f"=== budget reached: {state['n_papers']} papers, {state['n_ind']} indicators, "
        f"{state['n_measured']} measured, {state['n_gap']} gaps, "
        f"queue {len(state['queue'])}, cursor used {state['cursor_calls']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-seconds", type=int, default=39600)   # ~11h
    ap.add_argument("--max-cursor", type=int, default=60)
    ap.add_argument("--disk-min-gb", type=float, default=10.0)
    ap.add_argument("--resume", action="store_true")               # resume is automatic via state.json
    a = ap.parse_args()
    DISK_MIN = a.disk_min_gb
    run(a.budget_seconds, a.max_cursor)
