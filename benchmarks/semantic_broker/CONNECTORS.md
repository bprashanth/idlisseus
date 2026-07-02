# Connectors handed to Hermes (v-1 and beyond)

The connector list is legitimate to give Hermes — it is the *tool list*, not a
hint about which dataset answers which question (see the no-coercion rule in
[`PLAN.md`](PLAN.md)). Distractor connectors are included on purpose: choosing
the right connector, and *not* wasting time on the wrong one, is part of what
v-1 measures.

## Gold connectors (verified / to-wire)

| Connector | Access | Gives | Status |
|-----------|--------|-------|--------|
| **Earth Engine — FIRMS** | `ee` Python, `ImageCollection("FIRMS")` | active fire detections | EE auth **verified in-container** |
| **Earth Engine — ESA WorldCover** | `ee`, `ImageCollection("ESA/WorldCover/v200")` | 10 m land cover classes | **verified** (returned class 10 @ Nilgiris) |
| **Earth Engine — SRTM** | `ee`, `Image("USGS/SRTMGL1_003")` | terrain/elevation | **verified** (1518 m @ Nilgiris) |
| **Earth Engine — WDPA** | `ee`, `FeatureCollection("WCMC/WDPA/current/polygons")` | protected-area boundaries | **verified** (returned WG PA in AOI) |
| **GBIF** | public REST API `api.gbif.org/v1/occurrence/search` | species occurrence records (coords) | **verified** (247 Lantana occ. in Nilgiris bbox) |

**WDPA is reached through Earth Engine** (`WCMC/WDPA/current/polygons`), not the
Protected Planet REST API — so it needs no separate token and rides the EE auth
already in place. GBIF is a public API, no key.

**Earth Engine auth (done, verified end-to-end in a real agent run).** Three
things were required — each was a real gotcha:

1. **`earthengine-api` (+ `pymupdf`) preinstalled in the image.** The agent's
   `import ee` failed because auto-install-on-import can't map `ee`→`earthengine-api`
   (nor `fitz`→`pymupdf`). Baked into `hermes-agent-local` (see the Dockerfile).
2. **Creds at the *sandbox* HOME.** `execute_code` runs each script in a sandbox
   whose `HOME` is `{HERMES_HOME}/home` = **`/opt/data/home`** (Hermes' container
   HOME contract, `get_subprocess_home`), NOT `/opt/data`. So creds must be at
   `~/.hermes/home/.config/earthengine/credentials` (owned uid 10000). Staging
   them at `~/.hermes/.config` (the obvious spot) does **not** work.
3. **`~/.hermes` owned by uid 10000** so the agent can cd into `/opt/data`, and
   image `ENV HOME=/opt/data`.

With all three, the agent's `import ee; ee.Initialize(project="plantwars")` works
and real FIRMS/WorldCover queries return. Verified in the Q5 run.

## Distractor connectors (plausible, wrong for our questions)

Advertised alongside the gold ones to test discrimination:

- **Ocean SST / marine** (e.g. NOAA) — wrong ecosystem.
- **Air quality** (e.g. OpenAQ) — wrong domain.
- (optional) global night-lights / population — wrong signal.

A good v-1 result: Hermes ignores these. A bad one: it spends calls probing them.

## Container runtime notes (the fixes that made this work)

- Agent runs as **root** inside the container; the `~/.hermes` mount root is
  `0700 beeps`, so a non-root user can't even traverse it — do **not** force
  `--user 10000`.
- Package installs (`import ee`, etc. via uv) must not use the default
  `$HOME/.cache` — that mount path isn't agent-writable and was the cause of the
  earlier **pymupdf "failed to create directory"** failure. Redirect with
  `UV_CACHE_DIR` / `UV_PYTHON_INSTALL_DIR` to `/tmp` (baked into `run_v-1.sh`).
  This also means real PDF parsing (pymupdf) should now work in-agent.
