#!/usr/bin/env python3
"""preflight.py — does a fresh clone of idlisseus have what it needs to run?

Checks the cross-cutting prerequisites (model endpoint, Hermes image, connector auth,
python deps) and prints a PASS / WARN / FAIL line for each, then a summary. Nothing here
mutates state — it only inspects. Run it right after cloning, or when something breaks:

    python3 preflight.py

Exit code 0 if all REQUIRED checks pass (WARNs are allowed); non-zero if a required
capability is missing. Credentials/keys (Earth Engine, Dryad) are WARNs — the repo still
runs, but the capability that needs them is disabled, and we say so LOUDLY so a missing
key is never a silent, mysterious failure later.
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
GREEN, YELLOW, RED, BOLD, OFF = "\033[32m", "\033[33m", "\033[31m", "\033[1m", "\033[0m"
results = []  # (level, title, detail)  level in {"PASS","WARN","FAIL"}


def check(level, title, detail=""):
    results.append((level, title, detail))
    tag = {"PASS": f"{GREEN}✓ PASS{OFF}", "WARN": f"{YELLOW}⚠ WARN{OFF}",
           "FAIL": f"{RED}✗ FAIL{OFF}"}[level]
    print(f"{tag}  {title}")
    if detail:
        for line in detail.splitlines():
            print(f"          {line}")


# 1. Python -------------------------------------------------------------------------
if sys.version_info >= (3, 9):
    check("PASS", f"Python {sys.version_info.major}.{sys.version_info.minor}")
else:
    check("FAIL", "Python >= 3.9 required", f"found {sys.version.split()[0]}")

# 2. python deps used by paper_data (xlsx parsing) ----------------------------------
try:
    import openpyxl  # noqa: F401
    check("PASS", "openpyxl present (paper_data xlsx parsing)")
except ImportError:
    check("WARN", "openpyxl missing — paper_data can't read .xlsx/.xls datasets",
          "pip install openpyxl")

# 3. embeddings venv (discovery retrieval arm) --------------------------------------
embv = os.path.join(HERE, "benchmarks", "algebra", "paper_data_v-1", "embvenv", "bin", "python")
if os.path.exists(embv):
    check("PASS", "fastembed venv present (discovery embeddings arm)")
else:
    check("WARN", "fastembed venv missing — embedding/hybrid retrieval arms disabled",
          "python3 -m venv benchmarks/algebra/paper_data_v-1/embvenv && "
          "benchmarks/algebra/paper_data_v-1/embvenv/bin/pip install fastembed")

# 4. 122B model endpoint ------------------------------------------------------------
ENDPOINT = "http://172.17.0.1:8001/v1/chat/completions"
try:
    body = json.dumps({"model": "qwen", "messages": [{"role": "user", "content": "ok"}],
                       "max_tokens": 3, "chat_template_kwargs": {"enable_thinking": False}}).encode()
    req = urllib.request.Request(ENDPOINT, body, {"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=15).read()
    check("PASS", "122B endpoint reachable (172.17.0.1:8001, served name 'qwen')")
except Exception as e:
    check("FAIL", "122B endpoint unreachable at 172.17.0.1:8001",
          f"{str(e)[:70]}\nstart it: docker start vllm-qwen35  (see models/qwen3.5-122b/)")

# 5. Hermes image -------------------------------------------------------------------
if shutil.which("docker"):
    try:
        out = subprocess.run(["docker", "images", "-q", "hermes-agent-local"],
                             capture_output=True, text=True, timeout=15).stdout.strip()
        if out:
            check("PASS", "hermes-agent-local image built")
        else:
            check("WARN", "hermes-agent-local image not built — agent runs disabled",
                  "bash agents/hermes/build.sh")
    except Exception as e:
        check("WARN", "could not query docker images", str(e)[:60])
else:
    check("WARN", "docker not found — agent + model containers unavailable")

# 6. Earth Engine creds (connectors) ------------------------------------------------
# ~/.hermes is uid-10000 mode-700 (host user can't traverse it), so we can't stat the
# staged copy directly — the host-side ~/.config/earthengine/credentials is the readable
# signal that `earthengine authenticate` was run and can be staged.
ee_paths = [os.path.expanduser("~/.config/earthengine/credentials"),
            os.path.expanduser("~/.hermes/home/.config/earthengine/credentials")]
if any(os.path.exists(p) for p in ee_paths):
    check("PASS", "Earth Engine creds present (authenticate done; stage into ~/.hermes for the sandbox)")
else:
    check("WARN", "Earth Engine creds NOT found — EE-backed connectors (landcover, fire, "
          "greenness, terrain, embedding, hyperspectral) will fail",
          "earthengine authenticate, then stage to ~/.hermes/home/.config/earthengine/ "
          "(REPLICATION.md §3)")

# 7. Dryad creds (paper_data authenticated source + the paper_data SKILL) ------------
sys.path.insert(0, os.path.join(HERE, "benchmarks", "semantic_broker", "connectors"))
dryad_ok = False
try:
    import paper_data as _pd
    dryad_ok = _pd.dryad_configured()
except Exception as e:
    check("WARN", "could not import paper_data connector", str(e)[:60])
    _pd = None
if _pd is not None:
    if dryad_ok:
        check("PASS", "Dryad API creds configured (paper_data can download Dryad datasets)")
    else:
        check("WARN", f"{BOLD}Dryad API creds MISSING — the paper_data skill's Dryad path is "
              f"DISABLED{OFF}",
              "Consequences: no Dryad datasets in the corpus crawl (hop 3 SKIPPED), and Hermes "
              "cannot search Dryad at runtime. Zenodo/NCF still work.\n"
              "Fix: get client_id/client_secret at https://datadryad.org/account (ORCID login), "
              "then put them in ~/.config/idlisseus/dryad.json — see "
              "benchmarks/algebra/research/DRYAD_SETUP.md")

# 7b. eBird creds (bird occurrence + hotspot anchoring — a 'login' connector) ---------
try:
    import ebird as _eb
    if _eb.configured():
        check("PASS", "eBird API key configured (per-site bird observations + hotspots)")
    else:
        check("WARN", f"{BOLD}eBird API key MISSING — the ebird connector is DISABLED{OFF}",
              "Consequence: no per-site bird observations / hotspot anchoring (e.g. EBTL hotspot "
              "L36453021). GBIF birds still work but are coarser.\n"
              "Fix: free key at https://ebird.org/api/keygen -> ~/.config/idlisseus/ebird.json")
except Exception as e:
    check("WARN", "could not import ebird connector", str(e)[:60])

# 8. connectors present -------------------------------------------------------------
conn = os.path.join(HERE, "benchmarks", "semantic_broker", "connectors")
if os.path.isdir(conn) and os.path.exists(os.path.join(conn, "paper_data.py")):
    check("PASS", "connectors/ present")
else:
    check("FAIL", "connectors/ not found", conn)

# summary ---------------------------------------------------------------------------
n_fail = sum(1 for lvl, *_ in results if lvl == "FAIL")
n_warn = sum(1 for lvl, *_ in results if lvl == "WARN")
n_pass = sum(1 for lvl, *_ in results if lvl == "PASS")
print(f"\n{BOLD}=== preflight: {n_pass} pass, {n_warn} warn, {n_fail} fail ==={OFF}")
if n_fail:
    print(f"{RED}Required capabilities are missing (see FAIL above). The core stack won't run.{OFF}")
elif n_warn:
    print(f"{YELLOW}Core stack OK, but some capabilities are degraded (see WARN above).{OFF}")
    if _pd is not None and not dryad_ok:
        print(f"{YELLOW}In particular: the paper_data skill will run WITHOUT Dryad — "
              f"fewer papers, no runtime Dryad search.{OFF}")
else:
    print(f"{GREEN}All checks passed — full stack ready.{OFF}")
sys.exit(1 if n_fail else 0)
