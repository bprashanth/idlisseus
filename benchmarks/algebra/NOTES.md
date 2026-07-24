# The self-improving connector loop — 2h POC → 16h run

> Runnable version of the loop. Sits between [`EXPERIMENT_v-1.md`](EXPERIMENT_v-1.md)
> (Hermes runs wild; established *finding ≠ using*) and the v1 retrieval benchmark
> in [`PLAN.md`](PLAN.md). Its job: let a **frontier model manufacture a validated
> connector library + a ground-truthed `question→plan→answer→lineage` benchmark**,
> using **122b's failures as the spec sheet**. Correlational insights only — no
> causality, no future-spread prediction (explicitly out of scope).
>
> This doc is for the agent running the experiment. Read §0 first — it is the one
> thing that separates a real benchmark from one that certifies wrong answers.

---

## §0. The one rule (non-negotiable)

**A gold answer may only be minted from a connector that has passed a ground-truth
self-test.** Everything else in this doc can be POC-grade sloppy. This cannot.

Why: without it, a frontier connector-writer can hardcode a wrong legend (class 50
= "Shrubland" — frontier models make the *exact* v-1 Q5 error too), produce wrong
gold numbers, 122b later calls the same wrong connector, gets the same wrong
numbers, and the judge marks it **PASS**. You would spend 16 hours building a
benchmark that certifies hallucinations. The self-test is the anchor the whole
loop hangs from.

---

## §1. Goal — discover the algebra

You are not trying to hit a score. You are trying to *discover*, by watching what
questions require what, the **minimal set of primitives and connectors** that
covers a growing set of real conservation questions — each one validated.

Three concrete outputs:
1. **The algebra** — which primitives (FIND / LOOK UP / SUMMARISE-IN-AREA / RELATE
   / GROUP-RANK + whatever turns out to be missing, e.g. TREND) were actually
   needed, and by which questions.
2. **A validated connector library** — frozen expertise, each connector carrying a
   passing self-test.
3. **A benchmark ledger** — `question → plan → gold answer → lineage`, the most
   expensive thing to build by hand, produced here as a byproduct.

You do **not** need 100 questions up front. Seed with ~5–10; the Proposer harvests
100+ as the loop runs. A fixed list would kill the "generator pulls ahead"
dynamic.

---

## §2. The cast (roles → your infra)

| Role | Who | How you invoke it | Emits |
|------|-----|-------------------|-------|
| **Proposer** | frontier (you / cursor `agent`) | prompt with current library + bank | `(question, verified data source, intended plan)` just past the toolbox |
| **Solver** | Hermes + 122b | `run_v-1.sh "<question>"` (mounts `/opt/data/corpus:ro`, wires EE, no-coercion prompt) | `(plan, answer, confidence, trace)` — trace lands in `~/.hermes/state.db` |
| **Connector-writer** | frontier | triggered **only on Solver failure** | connector (Python+CLI, per [`CONNECTORS_DESIGN.md`](CONNECTORS_DESIGN.md) contract) **+ self-test** |
| **Judge** | frontier | compares Solver output to gold | `plan_match`, `number_match`, notes |
| **Session miner** | frontier | reads `state.db` across runs (16h only) | permanent playbook rules |

The Solver's competence is fixed (weights don't change). The Proposer and
Connector-writer are the frontier; **they are the factory, 122b's failures are the
spec.** "Catching up" means "the library now covers what's been asked" — not that
122b got smarter.

---

## §3. Verify a **connector** (the self-test) — operational

This is §0 made concrete. For every connector the loop writes:

**Fixture.** 3–6 points `(lat, lon, expected_value)` whose truth a human would bet
money on. You (frontier) can reason these out for unambiguous layers:

```
# landcover fixture (unambiguous — reason it out, no external check needed)
(11.017, 76.958, "Built-up")   # centre of Coimbatore city
(10.358, 76.890, "Tree cover") # Manamboli mature TR forest (from census asset)
(<a large reservoir>, "Water")
```

For fuzzier layers (e.g. greenness), test **direction/magnitude at a controlled
point**, not an exact value:

```
# greenness fixture
(intact mature forest pt)  -> ndvi_end high (>0.6) AND |slope| small   # stable
(known cleared/converted pt) -> slope < 0                              # dropped
```

**Test.** Assert `connector(point) == expected` (or within tolerance) for every
fixture point. All pass → connector trusted. **Any fail → connector REJECTED, do
not mint gold from it.** Where you have field data (e.g. the Manar survey's lantana
GPS points), use it as an extra fixture — a map value at a spot a botanist actually
stood on is the strongest ground truth you have.

**Meta-check (run ONCE, in the 2h version, before trusting any green self-test):**
deliberately corrupt a connector's legend (swap two class names) and confirm the
self-test **fails**. Only after you've watched the gate *catch* a bad connector
should you trust it passing. If the corrupted connector still "passes," your
fixture is too weak — add harder points.

The self-test doubles as a **regression guard**: when WorldCover ships v300 and
renumbers a class, the test breaks and surfaces the connector for a rewrite instead
of silently poisoning results.

---

## §4. Verify Solver **output** — operational

**Gold = run the tested connector chain yourself and capture numbers + lineage**
(which records, which connector+version, which params). This is exactly how the
QA/QB gold in [`QUERIES.md`](QUERIES.md) was produced (`Tree cover 186 · Built-up
40…`); you are formalizing it.

**Judge** compares Solver's `(plan, answer)` to gold on two axes:

- **`plan_match`** — did the Solver select the right connectors in a sensible
  order? *(robust primary signal: "did the system have the tools")*
- **`number_match`** — within tolerance: counts exact or ±1; rankings = top-k
  overlap or rank correlation; distributions = median within ±10%. *(the "insight
  is real" signal)*

Record both. **Never let the Judge accept "looks right" — it must re-run against
minted gold.** A lenient judge manufactures fake progress.

---

## §5. The struggle detector (the trigger) — operational

Read from a *completed* Hermes run:

- wall-clock runtime,
- did it emit a **final numeric answer**?,
- **failure phrases** in the answer: `"could not" / "unable" / "incomplete" / "as a
  proxy" / "gave up" / "fell back"`,
- (if wired) Hermes v0.18 completion-contract / verifier result.

**Rule (POC):** `struggled = runtime > T_struggle OR no_numeric_answer OR
failure_phrase_present`. Set `T_struggle ≈ 6–8 min` — v-1 saw correct
connector-assisted runs at **1m44s / 2m15s** and failures at **18–25 min**, so the
gap is wide and easy to split. **Capture the full trace regardless** (you need it
for session mining and for the ledger).

A clean solve → record PASS, done. A struggle → fire the Connector-writer (§3).

---

## §6. What to WAIT for (orchestration timing)

- **Hermes runs are minutes-long.** Launch `run_v-1.sh`, then **block until the run
  completes with a hard timeout** (kill at ~20 min). Do not fire-and-forget.
- **Then read the trace row** from `~/.hermes/state.db` — the run writes it on
  completion; that row is your `(plan, answer, trace)`.
- **Self-test:** seconds (one EE/API query per fixture point).
- **Gold mint:** one connector-chain run — seconds to minutes.
- **2h version: one Hermes run at a time.** Serialize; it's far easier to debug.
  (16h version may parallelize if EE quota allows — see §8.) EE rate/quota is a
  real constraint; treat it as the throughput ceiling.

---

# THE 2-HOUR VERSION

**Purpose:** prove the machine end-to-end at N=1 new connector + a handful of
questions. **Success = three things demonstrably work:** (1) the struggle detector
fires, (2) the self-test catches a *deliberately broken* connector, (3) a ledger
entry is genuinely re-runnable. Nothing about scale or score — just that the
plumbing and the two gates work.

Run two short tracks.

### Track A — validate the gate (~20 min)

Uses an existing connector with unambiguous ground truth (`landcover` — smallest,
already built, and the one that fixed the Q5 bug).

1. Write `landcover`'s self-test with the fixture in §3 (Coimbatore=Built-up,
   Manamboli=Tree cover, reservoir=Water). Run it → **expect PASS.**
2. **Corrupt it:** swap two class names in the connector's legend. Re-run the
   self-test → **expect FAIL.** Restore.
3. ✅ Outcome: you have *seen the gate catch a bad connector.* Now green self-tests
   mean something.

### Track B — validate the loop (~60–80 min)

Uses a connector that does **not** exist yet, so you actually watch failure →
write → retry. Target **`greenness` / timeseries** — it's the highest-value gap
(restoration recovery is the flagship question) and it produces the exact v-1
failure mode (hand-rolling an EE NDVI reduction).

1. **Stage:** pick a restoration-plot coordinate from the census/survival assets
   (e.g. Candura secondary forest, 10.309N 76.834E). Question:
   *"Is the Candura restoration plot greening up between 2019 and 2024?"*
2. **Solve (no greenness connector present):** `run_v-1.sh "<question>"`. It has
   landcover/fire/terrain/etc. but no NDVI-trend tool and no NDVI recipe → expect a
   struggle: either a hand-written EE reduction that loops/errors, or a failure
   phrase. **Detector fires.**
3. **Write connector:** frontier writes `greenness`:
   `trend(points, years) → +ndvi_slope,+ndvi_start,+ndvi_end`, owning the
   band/scale/cloud-mask (MODIS or Landsat NDVI). Write its self-test (§3 greenness
   fixture: intact-forest point stable-high; cleared point negative slope).
4. **Gate:** run the self-test → must PASS before proceeding. (If it fails, iterate
   the connector — this is the loop working, not a bug.)
5. **Mint gold:** run `greenness.trend` on the plot coords → real slopes + lineage.
6. **Re-solve (greenness now available + one playbook line pointing at it):**
   `run_v-1.sh` again → expect it to call `greenness.trend`, rank, finish fast.
   **Judge** vs gold → expect `plan_match=✓`, `number_match=✓`.
7. **Write the ledger entry (§7). Then re-run it from the ledger** to confirm it's
   reproducible.
8. ✅ Outcome: failure was detected, a validated connector was written to fix it,
   gold was minted from a *tested* chain, and the record replays.

If Tracks A and B both hold, the 16-hour run is the same machine with the clock
turned up.

---

# BRIDGE TO THE 16-HOUR VERSION

Same tick, plus **two new components** and some scaling. Nothing in §0–§6 changes —
the gates stay exactly as strict.

### Add 1 — the Curriculum Controller (the "generator pulls ahead" engine)

Track 122b's pass-rate on the current question bank. **When it crosses threshold
(e.g. ≥80% over the last K questions), signal the Proposer to emit a harder batch:**
a new data bucket, a new primitive *shape*, or a near-miss trap. This is what keeps
the frontier ahead and the library diversifying. Constrain every proposed question:

- (a) answerable by **overlay/correlation only** — reject anything needing causality
  or spread (out of scope);
- (b) grounded in a data source the Proposer has **actually located and verified is
  queryable** (see phantom-data guard below);
- (c) **not a near-duplicate** — check embedding similarity against the bank, reject
  dupes;
- (d) ideally just past the edge of the current toolbox (so it triggers a write).

### Add 2 — Session Mining → permanent rules (memory as rules, not embeddings)

Every hour (or every M failures), the miner reads `state.db` across *all* runs and
finds **repeated** failure patterns — e.g. "keeps forgetting `mkdir` for the work
dir," "queries FIRMS globally instead of near the points," "reinvents an NDVI
reduction that already exists." Convert each into a **permanent playbook rule /
config line** so it stops recurring. This is the automated version of the manual
fixes already logged in [`CONNECTORS_DESIGN.md`](CONNECTORS_DESIGN.md) ("issues
found + fixed") — you did session-mining by hand there; now the loop does it. These
rules compound: the *system* gets better even though the *weights* don't.

### Add 3 — the Scout (data-frontier discovery; the "unknown sources" path)

The Miner and Controller work *inside* the data you already have. The **Scout**
pushes the frontier *outward* — it finds sources not in the corpus yet. It is the
automation of VISION.md's unknown-sources path, and the highest-leverage /
highest-risk component: the only one that can make the loop answer genuinely new
questions, and the only one that can smuggle a hallucinated source past the gate.

**Demand-driven (pull) first, light speculative (push) second.** When the
Controller wants a harder question the current data can't support, that unmet need
is the Scout's *work order* ("find a canopy-height layer for this AOI", "find a
lantana-removal dataset with plot coords"). A light nightly sweep of the core
buckets (invasives / fire / land cover / restoration / biodiversity / governance)
adds serendipity. **Do not free-run a scraper** — that just builds a junk pile.

**Discovery ≠ trust — the Scout feeds the same §0 gate:**
- a downloadable file → a **known dump**: extract points, gold comes from the file;
- a platform layer → **unusable until a connector + self-test is written** for it.

**Two hard rules (tuned for a research POC):**
1. **Provenance is mandatory; license is NOT a gate.** This is a research project —
   community contributors routinely omit a licence out of negligence and supply one
   on request, so do not block on it. Instead **stamp every source at ingest,
   immutably**, on its card and the ledger `data_sources`: `source_url`,
   `retrieved_at`, `author_contact` (where findable), `license: "none|unknown|
   <spdx>"`. Preserved lineage is what makes "email the author for a licence /
   access before going live, or drop it" possible later. (Provenance lives on the
   card/ledger, stamped by the Scout — the Miner mines *failures*, not provenance;
   both are retained, by different parts.)
2. **Phantom-data guard on acquisition.** Nothing is admitted until the Scout has
   actually queried it and gotten rows back. A "found" source that returns nothing
   is discarded, never recorded as data.

**Where to look (queryable surfaces, best-structured first):**
- **CKAN servers** — `…/api/3/action/package_search`, a *uniform* API across every
  CKAN instance (incl. `data.gov.in`). The best structured discovery surface.
- **GBIF** — already the `occurrence` connector; Scout finds new taxa / datasets.
- **India Biodiversity Portal** (indiabiodiversity.org) — API, GBIF-linked.
- **Zenodo** — REST API + the NCF Western-Ghats community (our current spine).
- **ATREE** — datasets via web + IBP (less structured; download → known dump).
- **FSI / Bhuvan (ISRO)** — Indian forest-cover & remote-sensing products.
- research supplements (arXiv / journal) with lat/lon tables → known dumps.

**Out-of-AOI is a legitimate *harder mode*, if called out.** For difficulty the
Controller may pull sources from a *similar ecoregion outside the AOI* — the
correlation still teaches something. Make "similar" principled: use the **RESOLVE
Ecoregions** layer (EE). The AOI sits in *South Western Ghats montane rain
forests*; analogs are other polygons of the same ecoregion class (other
Western-Ghats massifs, montane wet-zone analogs). The answer must carry
`aoi_status: in_aoi | analog_ecoregion | out_of_aoi` + `analog_basis` and say it
plainly: *"this is outside your AOI, but in the same ecoregion, and the correlation
holds."* Honest transfer beats a false in-AOI precision.

### Scaling / operational

- **Parallelism:** run multiple Hermes questions concurrently **if EE quota allows**
  — quota is the real ceiling, not CPU.
- **Ledger** (§7) is append-only and *is* the durable deliverable — it's your
  benchmark and your lineage record at once.
- **Stop conditions:** 16h wall-clock, OR the Proposer can't find a new
  answerable-but-unsupported question after X tries (library saturated for the
  scoped data) — either is a legitimate finish.

### The three ways this quietly fails — run these as live checks

1. **Degenerate curriculum** — Proposer keeps emitting "classify X by land cover"
   variants. → enforce coverage across primitive shapes + buckets; reject dupes.
2. **Phantom data** — questions for data that isn't really there. → Proposer must
   verify the source is queryable *before* the question is admitted.
3. **Lenient judge = fake progress** — → Judge always re-runs numbers against minted
   gold; "the model said it looked right" never counts.

---

## §7. Ledger entry schema (the deliverable)

One JSON object per solved question, append-only:

```jsonc
{
  "id": "q0007-lantana-landcover",
  "question": "In what land cover does lantana mostly occur here?",
  "buckets": ["invasives", "land cover"],
  "primitive_shape": "FIND -> LOOK_UP -> GROUP",      // the plan skeleton
  "data_sources": [
    {"kind": "asset|connector", "ref": "queries/data/lantana_occurrence.csv | GBIF",
     "verified_queryable": true}
  ],
  "connectors_used": [{"name": "landcover", "version": "v200", "self_test": "pass"}],
  "plan": ["occurrence.search('Lantana camara', aoi)",
           "landcover.classify(points)",
           "groupby landcover, count"],
  "gold_answer": {"Tree cover": 186, "Built-up": 40, "Grassland": 17, "Cropland": 5},
  "solver_answer": { "...": "..." },
  "plan_match": true,
  "number_match": true,
  "confidence": 0.9,
  "coverage_envelope": {"n_points": 249, "in_data_gap": 0, "map_epoch": "2021"},
  "trace_ref": "state.db:run_1732",                   // full Hermes trace
  "generated_by": "cursor-agent",
  "solved_by": "hermes-122b",
  "ts_proposed": "...", "ts_solved": "...", "ts_gold_minted": "..."
}
```

`coverage_envelope` is the honesty field — carry it into any answer (e.g. QE's
"0/60 in PA" is a WDPA coverage gap, not a real result; the envelope makes that
explicit rather than reporting a false clean split). With the Scout (Add 3) it
also carries **`aoi_status`** (`in_aoi | analog_ecoregion | out_of_aoi`) +
`analog_basis`, so an out-of-AOI correlation is reported as exactly that. Each
`data_sources` entry additionally carries Scout-stamped **provenance** —
`source_url`, `retrieved_at`, `author_contact`, `license` (`none|unknown|<spdx>`,
recorded but never gated on) — the lineage that lets access be requested later.

---

## §8. The tick, in pseudocode

```
seed_bank = 5-10 questions (existing 5 + one Proposer batch)

for each open question q in bank:
    card   = card_maker(q.data_source)          # cheap 122b
    launch run_v-1.sh(q.question); WAIT(timeout=20min)
    trace  = read state.db latest run
    if struggled(trace):                        # §5
        conn, test = connector_writer(q, trace) # frontier, §3
        if not run(test): iterate conn until pass OR flag_human
        gold = run(conn_chain)                  # §4 — mint from TESTED chain
        register(conn)
        launch run_v-1.sh(q.question); WAIT      # retry WITH connector
        trace = read state.db latest run
    verdict = judge(trace.plan, trace.answer, gold)   # §4, re-runs numbers
    append_ledger(q, trace, gold, verdict)      # §7

    # 16h only:
    if hourly_tick: session_miner() -> new playbook rules   # Add 2
    if pass_rate(last_K) >= 0.80:
        bank += proposer.harder_batch()         # Add 1
```

---

## §9. What must be rigorous vs what can be sloppy

**Rigorous (do not cut corners):** the connector self-test gate (§0, §3) and the
Judge re-running numbers against minted gold (§4). These two are the entire
difference between a real benchmark and one that launders 122b agreeing with a
frontier hallucination.

**POC-grade is fine:** card format, drift between card and connector, storage,
parallelism, prompt polish. Don't spend the 2 hours there.

**Start with the 2-hour version.** If the detector fires, the self-test catches a
deliberately-broken connector, and a ledger entry replays — you have proven the
framework, and the 16-hour run is just the same loop left running.
