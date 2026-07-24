"""loop.py — the research discovery loop (bounded).

Each cycle, per theme: mine real papers (OpenAlex) -> extract indicators/questions
(cursor-agent) -> measure each against real data over time (GBIF/iNat/SoIB/EE
connectors) -> index to the KB with provenance. Failures/gaps are recorded as gaps
with a 'collect it / write a connector' suggestion, not skipped silently.

Bounded by --papers-per-theme and --themes; each cursor-agent + connector call is
timeout-wrapped, so it cannot hang. cursor-agent is paid cloud — keep counts low.

  python3 research/loop.py --aoi aois/elephants_by_the_lake.json --themes invasives,restoration --papers 2
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ALGEBRA = os.path.dirname(HERE)
SB = os.path.join(ALGEBRA, "..", "semantic_broker")
sys.path.insert(0, HERE)
import mine, measure, kb  # noqa: E402

THEME_QUERIES = {
    "invasives": "invasive alien plant Lantana dry deciduous forest India",
    "restoration": "dry deciduous forest restoration native species recovery India",
    "biodiversity": "bird butterfly diversity restoration indicator dry forest India",
    "water": "pond wetland odonata dragonfly water availability dry forest India",
    "elephants": "Asian elephant habitat corridor human elephant conflict Eastern Ghats",
    "livelihoods": "community livelihoods forest restoration income India rural",
    "nurseries": "native tree nursery seedling survival restoration India",
}


def compute_map_indicators(aoi, timeout=360):
    """Run greenness/fire/landcover once at the AOI center (real EE)."""
    lat, lon = aoi["center"]
    try:
        p = subprocess.run(
            ["docker", "run", "--rm", "--network", "host",
             "-v", f"{os.path.expanduser('~')}/.hermes:/opt/data",
             "-v", f"{os.path.abspath(os.path.join(SB, 'connectors'))}:/opt/data/connectors:ro",
             "-v", f"{os.path.join(HERE, 'sat.py')}:/opt/data/sat.py:ro",
             "-e", "HOME=/opt/data", "-w", "/opt/data",
             "--entrypoint", "/opt/hermes/.venv/bin/python3",
             "hermes-agent-local", "/opt/data/sat.py", str(lat), str(lon)],
            capture_output=True, text=True, timeout=timeout)
        return json.loads(p.stdout[p.stdout.index("{"):p.stdout.rindex("}") + 1])
    except Exception as ex:
        return {"error": f"map indicators unavailable: {ex}"}


def run(aoi_path, themes, papers_per_theme, budget_s):
    aoi = json.load(open(aoi_path))
    print(f"[map] computing satellite indicators for {aoi['label']} ...")
    map_ind = compute_map_indicators(aoi)
    print(f"[map] {map_ind}")

    start = time.time()
    n_papers = n_ind = n_measured = n_gap = 0
    for theme in themes:
        if time.time() - start > budget_s:
            break
        q = THEME_QUERIES.get(theme, f"{theme} {aoi.get('ecoregion','')} India")
        try:
            papers = mine.openalex_papers(q, per_page=papers_per_theme)
        except Exception as ex:
            print(f"[{theme}] paper mining failed: {ex}"); continue
        print(f"\n[{theme}] {len(papers)} papers")
        for p in papers:
            if time.time() - start > budget_s:
                break
            n_papers += 1
            inds = mine.extract_indicators(p["abstract"])
            print(f"  - {(p['title'] or '')[:70]}  -> {len(inds)} indicators")
            for ind in inds:
                n_ind += 1
                res = measure.measure(ind, aoi, map_ind)
                gap = bool(res.get("gap"))
                n_gap += gap; n_measured += (not gap)
                kb.append({"aoi": aoi["name"], "theme": theme,
                           "paper": {"title": p["title"], "doi": p["doi"], "year": p["year"]},
                           "indicator": ind, "result": res,
                           "status": "gap" if gap else "measured",
                           "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
                tag = "GAP" if gap else "OK "
                print(f"      [{tag}] {ind['indicator'][:48]:48s} via {ind.get('measurable_via')}")

    print(f"\n=== cycle done: {n_papers} papers, {n_ind} indicators, "
          f"{n_measured} measured, {n_gap} gaps. KB -> {kb.KB}")
    return {"papers": n_papers, "indicators": n_ind, "measured": n_measured, "gaps": n_gap}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--aoi", required=True)
    ap.add_argument("--themes", default="invasives,restoration")
    ap.add_argument("--papers", type=int, default=2)
    ap.add_argument("--budget-seconds", type=int, default=1800)
    a = ap.parse_args()
    run(a.aoi, [t.strip() for t in a.themes.split(",")], a.papers, a.budget_seconds)
