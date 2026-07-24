# Onboarding a new AOI — the overnight runbook

How to point the whole loop (connectors + Scout + Miner + Controller) at a new
area of interest and let it build that area's corpus overnight. Worked example:
`aois/elephants_by_the_lake.json` (Krishnagiri), onboarded 2026-07-03.

## What's AOI-agnostic vs AOI-specific

- **Agnostic (reused as-is):** every connector (they take a bbox/points, not a
  region), the self-test gate, `run_solver.sh`, `detect_struggle.sh`, the ledger,
  and all four components. *You do not fork code per AOI.*
- **Specific (the only thing you write):** one `aois/<name>.json` config. That's
  the whole per-AOI surface.

## Prerequisites (one-time, per box)

122B up (`vllm-qwen35`), `hermes-agent-local` built, EE creds staged (see
`../../REPLICATION.md`). Verify EE end-to-end in seconds:
`algebra/run_selftest.sh ../semantic_broker/connectors tests/test_landcover.py`.

## Step 1 — define the box

Pick `center` `[lat,lon]` and `bbox` `[west,south,east,north]` for the AOI (a
degree box around the property is fine; refine later).

## Step 2 — characterise it (this is what sets the questions)

Run two connectors on the bbox — both AOI-agnostic — and read the landscape off
the numbers:

```bash
SB=../semantic_broker/connectors
# ecoregion + biome (fills ecoregion/biome; also the analog-transfer key):
docker run --rm --network host -v ~/.hermes:/opt/data -v $PWD/$SB:/opt/data/connectors:ro \
  -e HOME=/opt/data -w /opt/data --entrypoint /opt/hermes/.venv/bin/python3 \
  hermes-agent-local -m connectors.ecoregion covering --bbox <w,s,e,n>
# land-cover mix (fills landscape; tells you which buckets matter):
#   ...same run... -m connectors.landcover area_by_class --bbox <w,s,e,n>
```

The land-cover mix drives the **bucket weights**. Krishnagiri came back Cropland >
Tree cover > Shrubland (dry, fragmented) → weight **connectivity** (elephant
corridors) and **dry-zone invasives** high, wet-forest **restoration** low. A wet
AOI (Anamalai: 74% Tree cover) would weight restoration/recovery high instead.

## Step 3 — write the config

Copy `aois/template.json` → `aois/<name>.json`; fill `center`, `bbox`,
`ecoregion`, `biome`, `landscape`, `seed_species` (put the invasive **and** the
flagship; the Proposer picks the right one per bucket), `buckets` (weighted by
what step 2 showed), and `catalogs` (CKAN bases to search — India: `data.gov.in`).

## Step 4 — bootstrap (fast, no LLM call)

```bash
python3 components/loop.py --aoi aois/<name>.json
```

Writes `aois/<name>/`:
- **`sources.json`** — Scout's verified data frontier. GBIF species that returned
  rows are *available*; zero-row species are *phantom* (flagged, never treated as
  data); CKAN datasets with provenance stamps. **Provenance (source_url,
  retrieved_at, license) is recorded on everything** — license is never a gate
  (request it from authors before going live, or drop the source).
- **`questions.jsonl`** — the Controller's first bank, each tagged
  `answerable_now` / `needs_connector` / (data_needs).
- **`playbook_rules.md`** — the Miner's rules from past run logs.
- **`bootstrap_report.md`** — the human summary; **read this first.**

## Step 5 — read the report, then run overnight

The report tells you, for this AOI:
- what's **answerable now** (library covers it) → these get solved for gold;
- what **needs a connector** — including **breaker primitives** the AOI demands
  (Krishnagiri surfaced **NETWORK** for elephant-corridor connectivity and
  **PATTERN** for forest–cropland fragmentation; neither exists yet).

The overnight loop is `driver.py`. Do a **dry-run first** (mints gold from tested
connectors, no LLM — fast, proves the bank is executable), then the **live** run:

```bash
# dry-run: gold + ledger + queues, no Hermes (minutes)
python3 driver.py --aoi aois/<name>.json --dry-run

# live 16h: adds run_solver.sh (Hermes) + struggle-detect + judge per question
python3 driver.py --aoi aois/<name>.json --live --budget-seconds 57600
```

Per question the live driver: mints gold via `goldmint.sh` (tested connectors) ->
`run_solver.sh` (hard-timeout, can't hang) -> `detect_struggle.sh` -> judge vs
gold -> append `ledger/<name>_ledger.jsonl`. It sorts questions into **solved**,
**needs_input** (supply a point set), and **connector_demand** (a breaker /
missing connector the frontier must write + self-test before that question counts).
The Controller escalates at pass-rate ≥ 0.80; the Miner re-mines each few ticks.
A `needs_connector`/breaker question is *surfaced*, not auto-answered — writing
NETWORK/PATTERN connectors (+ their self-tests) is the frontier's job between runs.

## The rules that never bend (regardless of AOI)

- **A gold answer only comes from a connector that passed its ground-truth
  self-test** (NOTES §0). New primitive (NETWORK/PATTERN) ⇒ new connector ⇒ new
  self-test before any gold.
- **Provenance mandatory, license not.** (Add 3.)
- **Out-of-AOI is allowed as a *harder mode* only if called out** — use
  `ecoregion.analog_points(same_ecoregion, exclude=this_bbox)` and tag the answer
  `aoi_status: analog_ecoregion`.
- **Phantom-data guard** — a source that returns no rows is never admitted.

## Onboarding a second AOI = repeat steps 1–5 with a new JSON. No code changes.
