# ds4 (DeepSeek V4 Flash, local) vs Cursor Agent (hosted) — benchmark

Run on this DGX Spark, comparing `ds4-agent` (local coding agent shipped with ds4/DwarfStar,
running DeepSeek V4 Flash q2-imatrix on the GPU) against `agent` (Cursor's hosted coding-agent
CLI). Three tasks, identical prompts where the task allowed it. Raw outputs and transcripts are
in the sibling `task1_coding/`, `task2_form_extraction/`, `task3_literature/` directories.

## Infra notes that shaped methodology

- ds4/DeepSeek V4 Flash is **text-only** — no vision. Confirmed by inspecting ds4's own docs and
  by directly testing it (see Task 2).
- This DGX Spark has **unified CPU/GPU memory**. Loading the ~80GB model occupies most of the
  121GB total RAM, so ds4-agent (which loads its own model copy) could not run concurrently with
  `ds4-server` (the Odysseus-facing inference daemon from the main POC). `ds4-server` was stopped
  before each ds4-agent run and restarted afterward.
- Every fresh `ds4-agent` invocation pays a fixed ~20s cost to load the 80GB model into GPU memory
  before doing any work. Cursor's agent, talking to a hosted API, has no equivalent cost.
- ds4's measured single-stream decode speed is ~15 tokens/sec, with no request batching (see the
  main POC's concurrency test) — this directly explains why ds4-agent is consistently slower than
  Cursor on tasks requiring long output, independent of reasoning quality.

## Task 1 — Coding: download a dataset, build a dashboard

Prompt (identical for both): download `tips.csv` from a public URL and build a self-contained
`dashboard.html` (scatter, bar, and distribution charts) plus the `build_dashboard.py` used to
generate it.

| | Cursor agent | ds4-agent |
|---|---|---|
| Wall time | **65s** | 228s (2nd attempt; see below) |
| Correct output | Yes | Yes |
| Self-contained (works offline)? | **Yes** — Plotly inlined, 4.86MB file | **No** — links `https://cdn.plot.ly/...`, 9.9KB file, requires internet despite the instruction |
| Real dataset used | Yes (244-row tips.csv, verified) | Yes (244-row tips.csv, verified) |

ds4-agent's first attempt chose to hand-roll an SVG charting library in pure Python (no
matplotlib/pandas assumed) rather than use a plotting library. That is far more code to generate
token-by-token at ~15 tok/s, and the attempt was still mid-file when it hit my test harness's
5-minute cap. The second attempt switched to Plotly-via-CDN and finished in 228s — still ~3.5x
slower than Cursor, and it didn't fully honor the "self-contained" instruction the way Cursor's
did. ds4-agent also saved the downloaded CSV to `/tmp/` rather than the working directory; minor,
but Cursor's output is the tidier deliverable.

## Task 2 — Form recognition: extract a handwritten field datasheet to Excel

Source: a 3-page scanned PDF of 6 handwritten "100x100m grid" ecological survey forms (checkmarks,
X marks, circled multiple-choice answers, hand-drawn quadrant diagrams).

**Cursor agent** (native multimodal vision, given the PDF directly): 324s. Produced
`extraction.xlsx` with one row per form, 16 columns (grid_no, date, observer, GPS, altitude,
slope, canopy density/composition, disturbance, per-species alien-tree presence by quarter, and
free-text prevalence notes). Cross-checked against the source images:
- 5 of 6 grid numbers correct (`M13`, `L13`, `K11`, `N15`, `M15`); one error — wrote `JH-02`
  for what is actually `J11-02`.
- Dates, observers, and GPS coordinates all matched the handwriting.
- Correctly wrote `illegible` for one observer field that is genuinely blank in the source,
  rather than guessing.
- Quarter-by-quarter checkmark/X patterns for the alien-tree and prevalence tables matched the
  source closely on spot-check.

**ds4-agent, attempt A (given the raw PDF directly):** ds4/DeepSeek V4 Flash has no vision, so it
could not view the PDF. Rather than refusing outright, it used its own bash tool to run
`pdftotext`/OCR itself, got the same garbled handwriting-OCR output a human would get from
`tesseract`, recognized the OCR was failing, and then attempted an infeasible workaround —
inspecting raw pixel values via PIL to "read" the handwriting manually. This is a genuinely
resourceful agentic response to a tool gap, but it cannot substitute for vision; the run was
capped after it entered an unproductive loop of pixel-level guessing
(`task2_form_extraction/ds4/ds4_transcript_direct_pdf.log`).

**ds4-agent, attempt B (fairness test — given the same OCR text I generated separately via
`pdftoppm` + `tesseract`):** 605s. Reasoned carefully and conservatively over the OCR text,
correctly recognizing when fields could not be determined rather than confabulating — but the
OCR itself was too degraded to recover most fields (handwritten checkmarks, circled multiple-choice
words, and most numerals OCR'd as garbage characters). Result: 4 of 6 rows came back entirely
`illegible`; 0 of 6 grid numbers were recovered correctly (closest approximations like `£13` for
`L13` and `Mis` for `M15` were OCR artifacts copied verbatim, not corrected); canopy density was
`illegible` in all 6 rows because "which word is circled" is a visual signal that plain-text OCR
cannot carry at all.

**Verdict for this task:** the gap is structural, not a reasoning-quality gap. Cursor's native
vision reads the source directly; ds4 is fundamentally blind to it. No amount of prompting fixes
that — only adding a real vision pipeline (or using DeepSeek's vision-capable siblings, if any)
would close it.

## Task 3 — Literature: 2-3 paragraph short fiction

Identical prompt: an old lighthouse keeper realizing his lighthouse is about to be automated away.

| | Cursor agent | ds4-agent |
|---|---|---|
| Wall time | 23s | 67s |
| Quality | Strong — concrete imagery, coherent arc, restrained ending | Strong — concrete imagery, coherent arc, similar emotional beat (a wife memory, a final ritual) |

This is the smallest gap of the three tasks — once vision and heavy multi-step tool orchestration
aren't required, ds4/DeepSeek V4 Flash produces prose that's qualitatively comparable to Cursor's
underlying hosted model, just ~3x slower in wall-clock time (consistent with the ~15 tok/s
single-stream ceiling vs a much higher-throughput hosted endpoint).

Excerpts:

> **Cursor:** "On the morning the letter arrived, Elias climbed the spiral stairs as he had every
> dawn for forty years, his knees protesting the familiar ascent, his hands finding each worn rail
> without thought..."

> **ds4-agent:** "The morning light came gray and grudging through the fog, as if the sea itself
> were reluctant to begin another day. Elias stood at the top of the spiral stair, coffee cup warm
> against his palm, and watched the beam of the old Fresnel lens pulse once more into the brine..."

(Full text in `task3_literature/cursor/story.txt` and `task3_literature/ds4/story.txt`.)

## Overall verdict

- **Vision-required or vision-helpful tasks:** Cursor wins decisively — not a matter of degree.
  ds4 is text-only; anything involving images, scans, or handwritten/printed source documents
  needs an external OCR/vision pipeline bolted on, and even then quality is capped by what
  survives OCR (visual cues like circled answers are lost entirely).
- **Pure text/code tasks of comparable scope:** both get to a correct answer, but Cursor is
  consistently 3-4x faster in wall-clock time (no model-load cost, much higher token throughput)
  and, in Task 1, followed the literal instructions ("self-contained") more faithfully.
- **Where ds4 is the right tool anyway:** fully local/offline operation, no per-token cost, no
  data leaving the machine — relevant if the workload is privacy-sensitive or if API costs at
  scale matter more than 3-4x latency. ds4-agent's reasoning quality and tool-use discipline
  (esp. its honest "illegible" rather than confabulating in Task 2) were genuinely solid; the
  gap here is throughput and the lack of vision, not the model's judgment.
- **Practical caveat specific to this machine:** because GPU and system RAM are unified here, ds4
  cannot run alongside other memory-heavy work (including its own server process). Any local
  deployment plan needs to account for that exclusivity, not just raw model quality.
