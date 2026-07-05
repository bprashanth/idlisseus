# Connector philosophy — how to build & update one

Living guide. Update it whenever building/testing teaches us something.

## Why connectors exist

v-1 ([`../EXPERIMENT_v-1.md`](../EXPERIMENT_v-1.md)) showed raw Hermes *finds* the
right data but fails the *analysis*: it invents legends (class 50 ≠ "Shrubland")
and can't write the Earth Engine reductions (Q1 burned 25 min and gave up). A
connector moves that competence out of the model and into small, tested code.

## Invariants (the philosophy)

1. **Points in, points out.** A connector takes a CSV of points (`lat`,`lon`) and
   returns the same rows + new columns, *or* it **produces** points. It never
   returns an Earth Engine object or raw API JSON across the boundary.
2. **Own the metadata.** Legends, band names, dataset IDs, thresholds are
   hardcoded **and verified** inside the connector — never left for the agent to
   guess. Guessing is exactly what fails.
3. **Self-describing.** `describe()` / `--describe` emits purpose, dataset,
   legend, signatures, one example, gotchas, and coverage warnings. The agent
   *discovers* metadata; it does not invent it.
4. **One concept per connector = one column-family.** `landcover.classify`→
   `landcover`; `fire.exposure`→`fire_count`. Small and composable beats clever.
5. **Hide the engine.** `ee.Initialize()` is internal. The agent never imports `ee`.
6. **Disclose limits loudly.** If the source can't cover the AOI/question (e.g.
   WDPA in India), say so in `describe()` *and* return honest values. Sometimes
   the correct insight is "this source can't answer it" — that beats a clean lie.
7. **Ranking over false precision.** Return metrics honest for *ranking*; document
   when a number is not an absolute (`fire_count`, occurrence density).

## What a connector must return

- CSV/JSON rows with stable columns; new columns named by concept.
- On failure: a structured `{"error": "...", "hint": "..."}`, never a traceback.

## How Hermes uses it successfully

Read [`PLAYBOOK.md`](PLAYBOOK.md) (the pattern) + the connector's card. Then:
**get points → annotate with connector(s) → group/rank with pandas.** Never write
Earth Engine code; run `--describe` to get a legend. Invocation:
```
python /opt/data/connectors/<name>.py <function> --points in.csv --out out.csv
python /opt/data/connectors/<name>.py --describe
```

## How to ADD a connector

1. Copy `landcover.py` (the reference); use `_base.read_points/write_points` so
   you speak the points-in/points-out contract for free.
2. Implement functions over list-of-dicts points.
3. Hardcode the metadata and **verify it against a known point** before trusting it.
4. Fill `describe()` completely — legend, gotcha, coverage.
5. Write `<name>.md` (uniform card template) and add the connector to `PLAYBOOK.md`.
6. Test live. Anything surprising → document it (next section).

## How to UPDATE a connector

Update when testing reveals a wrong legend/band, a coverage gap, a misleading
metric, or a better default. **Rule: every surprise found in testing becomes a
documented `gotcha`/`coverage_warning`, not silent behaviour.** Keep the code,
`describe()`, and the `.md` card in lockstep.

## Lessons banked while building (2026-07)

- **import-name ≠ pip-name** → preinstall in the Hermes image (`ee`→earthengine-api,
  `fitz`→pymupdf); auto-install-on-import can't map them.
- **Sandbox HOME is `/opt/data/home`** → EE creds/config live there.
- **Legends must be owned** — the model *will* invent class codes otherwise (Q5).
- **Data coverage is a first-class output** — WDPA lacks Western-Ghats reserve
  boundaries; the connector discloses it and points to `geo.within` on a supplied
  GeoJSON rather than fabricating an inside/outside split.
- **Zero can be signal** — wet evergreen sites returning 0 fire is correct, not a bug.

## Lessons banked from the algebra loop (2026-07-03, `greenness`)

- **TREND is a distinct primitive.** "Is it recovering?" is a *slope over years*,
  not a map lookup — the first thing the FIND/LOOK-UP/SUMMARISE/RELATE/GROUP set
  can't express. `greenness.trend` owns the annual compositing + the least-squares
  fit so the agent never hand-writes a per-year EE reduction (which is exactly what
  it hung 20 min on with no connector).
- **Self-test fixtures for a fuzzy layer test direction/magnitude, not an exact
  value** (NOTES §3): intact forest → NDVI high & flat; city → low; water → very
  low. The bounds are chosen so a **broken scale factor** (0.0001 dropped → values
  in the thousands) blows the ceiling and the gate rejects it. Verify fixture bounds
  by *running the connector first*, then set them — don't guess.
- **NDVI saturates over dense canopy** → a mature intact forest reads
  *high-and-flat*, which is not "failing to recover." Read `trend_class` together
  with `ndvi_end`; documented as the connector's `gotcha`.
- **A gold answer is only as trustworthy as the self-test that gates it** (NOTES
  §0). Mint gold *only* from a connector whose ground-truth self-test passes; the
  meta-check (deliberately break it, confirm the test fails) is what makes a green
  test mean something.
