# Model experiments

Three benchmark rounds run on this box. Each has its own `PLAN.md` (methodology + rationale),
most have a `CHECKPOINT.md` (append-only run log — read this first if picking up an interrupted
run), and a `REPORT.md` (findings + verdict). This page is the index, the exact prompts, and the
replication steps — read the linked `REPORT.md` for full narrative results.

## Benchmark 1 — ds4-agent vs Cursor agent (`benchmark/`)

**Question:** is the local model/agent (`ds4-agent` + DeepSeek V4 Flash) competitive with a
hosted coding-agent CLI (Cursor) on ordinary agent tasks?

**Verdict (full detail in `benchmark/REPORT.md`):** Cursor wins decisively on anything requiring
vision (ds4 is text-only); roughly comparable, ds4 slower, on pure text/code tasks.

| Task | Exact prompt | Assets |
|---|---|---|
| 1. Coding | *"Download the dataset at https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv (it's a small CSV of restaurant tips). Then build a single self-contained dashboard.html file (no server needed, just open in a browser) with a few charts summarizing the data: total bill vs tip scatter plot colored by smoker status, average tip percentage by day of week, and tip amount distribution by gender. Also save the python script you used to generate it as build_dashboard.py."* | `benchmark/task1_coding/{cursor,ds4}/` |
| 2. Form extraction | *"Attached is a scanned PDF (GridVegetation100mx100m.pdf, 3 pages, 6 handwritten 'Data sheet for 100 x 100 m grid' forms) of handwritten ecological field datasheets. Read the handwriting carefully and extract the data into an Excel file called extraction.xlsx with one row per grid sheet, columns: grid_no, date, observer, gps_lat, gps_lon, altitude, slope, canopy_density, canopy_composition, disturbance, alien_trees_silver_oak, alien_trees_maesopsis, alien_trees_spathodea, alien_trees_eucalyptus, alien_trees_other_species, alien_plant_prevalence_notes (a free text summary of the cover/quarter table for Lantana, Chromolaena, Mikania, Wedelia, Montanoa, Gliricidia, and any 'other' rows like Polygonum). Use your best judgement transcribing checkmarks/X marks/circled words; note any illegible fields as 'illegible' rather than guessing. Use openpyxl or pandas. Save the extraction.xlsx file in this directory."* | `benchmark/task2_form_extraction/{cursor,ds4}/`, source PDF in same dir |
| 3. Literature | *"Write a 2-3 paragraph piece of literary fiction. Theme: an old lighthouse keeper on a remote coast realizes the lighthouse he has tended for forty years is about to be automated and decommissioned. Write only the piece itself, no preamble or commentary, and save it to story.txt."* | `benchmark/task3_literature/{cursor,ds4}/` |

**To replicate:** `agent -p --force "<prompt>"` for Cursor; `ds4/ds4-agent -m ds4/ds4flash.gguf
--non-interactive --chdir <dir> -p "<prompt>"` for ds4 (stop `ds4` service first).

## Benchmark 2 — Hermes vs raw ds4-agent; ds4 vs Nemotron-3 (`benchmark2_hermes/`)

**Question:** does the agent harness matter independent of the model, and does the model matter
independent of the harness? Real agentic task: search, download, and synthesize a literature
corpus with no pre-given documents.

**Verdict (full detail in `benchmark2_hermes/REPORT.md`):** raw `ds4-agent` was fastest and most
reliable (25 min, zero friction). Hermes+ds4 worked but 3x slower with real tool-call friction.
Hermes+Nemotron-3 **did not complete** — hit its turn budget after 1h52m due to a confirmed
speculative-decoding throughput collapse at long context (see `models.md`).

**Exact prompt** (identical across all three runs):

> *"Research wildfire risk interventions for the Nilgiris and broader Himalayan region. Find and
> download roughly 10 relevant papers and a few reports yourself - a couple of reliable starting
> points to consider are Zenodo and NGO publications on wildfire/forest-fire management in this
> region, but do not limit yourself to those, search wherever is useful. Save everything you
> download into a subdirectory called wildfire_research in your current workspace, so it can be
> audited afterward. Then answer: what interventions are supported by evidence? What
> disagreements exist in the literature? What would you recommend measuring? Support your claims
> with a dashboard (an HTML file is fine). Include citations to the specific documents you
> downloaded."*

Deliberately *not* told what to download or where — the corpus itself is part of what's being
tested.

**Assets:**
- `benchmark2_hermes/hermes_results/` — Hermes+ds4's downloaded corpus (20 PDFs), dashboard,
  full transcript.
- `benchmark2_hermes/ds4_agent_run/wildfire_research/` — raw ds4-agent's downloaded corpus (20
  PDFs, different/messier filenames than Hermes's renamed set), dashboard, transcript.
- `benchmark2_hermes/hermes_nemotron_results/` — Hermes+Nemotron-3's partial output (only 2
  PDFs — it never finished).
- `benchmark2_hermes/PLAN_MODEL.md` — the generalized, parameterized procedure (download → smoke
  test → Hermes tool-calling test) this round's setup steps were condensed into, for trying any
  future model the same way.

**To replicate:** see `models.md` for bringing up each model; then either
`ds4/ds4-agent -m ds4/ds4flash.gguf --non-interactive --chdir <dir> -p "<prompt above>"` (raw),
or `docker run --rm -v ~/.hermes:/opt/data nousresearch/hermes-agent chat -q "<prompt above>"`
(Hermes, after pointing it at the target model per `agents.md`). Expect 25min-2hr+ depending on
model — this is a long, open-ended task, run it backgrounded and check on it periodically.

## Benchmark 3 — Seed-OSS-36B vs ds4, document synthesis (`benchmark3_seed_oss/`)

**Question:** motivated by "maybe a smaller dense model is better for quick literature-synthesis
tasks via Odysseus, even if not for long agentic work." Deliberately *not* repeating Benchmark
2's agentic-search task — this isolates synthesis quality on a **fixed, known document set**, no
search/download, via direct API calls only (no agent harness in the loop at all).

**Verdict:** ds4 was faster on every single task, by the widest margins on the *short* queries
the hypothesis was specifically about (13-20x faster on trivial prompts; 2.6-6.4x on document
tasks). Quality was comparable to slightly better for ds4 on the disagreement-finding task. Full
elapsed-time table and quality notes are in `benchmark3_seed_oss/CHECKPOINT.md` (final entries);
a standalone `REPORT.md` for this round had not been written as of this doc pass — check whether
one exists before assuming this summary is the latest word.

**Document set:** 5 papers reused from Benchmark 2's already-downloaded wildfire corpus (not
re-downloaded), copied + text-extracted via `pdftotext` into `benchmark3_seed_oss/papers/`:
`01_Models_Forest_Fire_Management_India`, `03_Forest_Fire_Himalayan_Regions`,
`09_Wildfire_Burn_Severity_Uttarakhand`, `11_Cloud_Based_Fire_Alert_IoT`,
`16_Madhuca_Longifolia_Fire_Cause` — the last one was picked deliberately to create a real
disagreement angle against the first (Mahua-flower-collection-as-specific-cause vs.
general-anthropogenic-cause framing).

**Exact prompts** — all five are defined verbatim in `benchmark3_seed_oss/run_task.py`'s
`build_prompt()` function (read it directly for the exact wrapper text + which documents are
concatenated into each prompt; not fully reproduced here because tasks 2/4 embed all 5 full
paper texts inline, making the literal prompt tens of thousands of characters):

1. **Single-doc summary** — summarize `03_Forest_Fire_Himalayan_Regions` in ~3 paragraphs.
2. **Multi-doc synthesis** — given all 5 papers' text, identify agreements/disagreements/
   contributions, citing papers by document name.
3. **Targeted Q&A** — given only `01` and `16`'s text, what do they say about fire causes, do
   they agree/disagree, and explicit instruction to say "not stated" rather than guess.
4. **One-shot dashboard** — given all 5 papers' text, produce a complete self-contained
   `dashboard.html` as the response text (no tool use — this tests one-shot generation, not
   agentic file-writing).
5. **Short-prompt latency** — three trivial, document-unrelated prompts: *"What is 2+2?"*,
   *"Name three colors."*, *"Spell the word banana backwards."* — run identically against both
   models for direct apples-to-apples timing.

**Assets:**
- `benchmark3_seed_oss/papers/` — the 5 source PDFs + their `pdftotext`-extracted `.txt` files.
- `benchmark3_seed_oss/run_task.py` — the exact prompt-building + API-call harness used; this
  *is* the replication script.
- `benchmark3_seed_oss/seed_oss_results/` and `ds4_results/` — prompt+response pairs for every
  task (`taskN_prompt.txt`, `taskN_response.txt`, `taskN_response.json` with token usage),
  `task4_dashboard.html` (extracted from the model's markdown-fenced response), `task5_latency.txt`.

**To replicate:**
```bash
cd benchmark3_seed_oss
python3 run_task.py 1 http://172.17.0.1:8000/v1 <model-name> <output-dir>   # tasks 1-4
# task 5 is a few inline curl/python calls — see run_task.py's call() function as a template
```
Point `<model-name>`/the URL at whichever model is currently running (`models.md`). **Use a long
client-side timeout** — Seed-OSS's slower decode meant the document tasks took up to ~28 minutes
each; a too-short client timeout produced a spurious-looking "failure" twice during the original
run that was actually just the client giving up early while the server kept working correctly
(confirmed via `nvidia-smi` showing sustained GPU utilization + vLLM's own throughput logs both
times). `run_task.py`'s timeout is already set to 3600s for this reason — don't reduce it without
checking the model's actual decode speed first.

## General tips for running these experiments

- **Always run the model-pair's go/no-go smoke tests before the real task** (`agents.md`) — every
  real failure caught in this repo (Nemotron's speculative-decoding collapse, the timeout bugs in
  our own harness) was caught by checking actual server-side signals (`nvidia-smi`, vLLM's own
  throughput logs, `.incomplete` blob mtimes) rather than assuming a slow/stuck-looking client
  meant the model had failed.
- **A request that "isn't responding" might just be slow, not stuck** — before declaring a
  failure, check `nvidia-smi --query-gpu=utilization.gpu --format=csv` (high = genuinely
  computing) and the model server's own logs for ongoing throughput. Only treat it as a real
  stall if both are flat for an extended period.
- **Long unattended runs need a judgment-call cutoff.** Don't let an open-ended agentic task run
  indefinitely on the assumption it'll eventually finish — if it's burned multiples of a
  comparable run's total time with proportionally little progress, stopping and documenting the
  partial result honestly (Benchmark 2's Nemotron run) is itself a valid, reportable finding.
- **Save raw transcripts/JSON, not just your own summary** — every report in this repo was
  written by re-reading actual saved output, not from memory of what a run "seemed" to produce.
