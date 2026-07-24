# Skill algebra — how we categorise DSS skills (and explain them in /why)

Every skill/tool we build answers a **spatial-ecological question of a known TYPE**. Classifying by type
(not by dataset) keeps skills from being shoehorned, tells us what's missing, and gives `/why` a
per-type explanation template. **New skills MUST declare their bucket(s) + the /why template below.**
This doc is the contract; fork it into the DSS repo as the skill taxonomy.

## The buckets

| Bucket | The question | Baseline / signal | Connectors today | /why template |
|---|---|---|---|---|
| **STATE** | *Where is X now?* | presence, or fine-grained appearance | `occurrence`, `predict.presence`, `invasive` (spatial), `s2` | "detected X by [records \| appearance-signature]; source …; confidence [data\|model]" |
| **RELATION** | *X relative to Y?* | proximity / containment | `geo` (cooccur/within/buffer) | "measured [distance\|overlap] of X to Y; proximity = shared-habitat proxy" |
| **CHANGE** | *Divergence from expected?* | expected spatio-temporal baseline → the deviation | `invasive` (phenology), `s2.anomaly` | "baseline = [expected, e.g. dry-season senescence]; signal = [deviation, e.g. stay-green]; truth = …" |
| **TREND** | *Trajectory over time?* | slope of a time series | `greenness` | "N-year slope of [metric]; direction/strength" |
| **VALUE** | *How much / how dense?* | magnitude at a scale/time-step | `s2` (density), `water`, `terrain` | "magnitude of [metric] at [scale, time-step], labelled as measured" |
| **TRANSFER** *(modifier, not a bucket)* | *Infer where labels are absent* | donor labels → analog target, gated | `predict.gate/route`, RF/SDM, `embedding` | "transferred from [donors] to [target]; gate [analog/climate] = 0.x; MODELLED not observed" |

**TRANSFER cross-cuts everything** — it's how any bucket copes with data scarcity (our core constraint).
A skill is `BUCKET (+ TRANSFER)`. Confidence always drops when TRANSFER is involved, and `/why` must say so.

## GROUND-TRUTH (the verify lens) — a second cross-cutting layer, on OUTPUT

Whenever a bucket puts a **modelled/transferred** signal on the ground — invasive likelihood, SDM/RF
suitability, a colocation surface, a greening trend — it should be able to emit a **ground-truth lens**
instead of just numbers: a self-contained map showing **every method's prediction** (toggle between them)
with a **cursor lens onto high-res imagery**, so the user eyeballs what's actually there. Often the answer
is obvious in that one view; when the hot cells sit on orchards/scrub instead of thickets, the transfer is
visibly wrong. This is `connectors/groundtruth_lens.py` — reusable across **STATE / RELATION / CHANGE /
TREND** (invasives, "what grows here", "where is X vs Y", "is Y greening"). It is **static HTML** (image +
layers embedded), so the agent hands back a file/link with no server and no RAM cost. The rule: **any
answer that shows multiple transfer methods should offer the lens** — it's how we make TRANSFER honest to a
human. Points to verify against come from `occurrence` (GBIF) **and iNaturalist directly** (richer for
well-visited sites — EBTL has 218 iNat obs where GBIF research-grade had ~0 for Lantana).

## Worked example — the invasive map is two buckets, cross-validated

- **Approach 1 = CHANGE + TRANSFER:** natives senesce in the dry season, invaders stay green (the deviation);
  RF signature transferred from GBIF records 20–40 km away. Free (S2/AlphaEarth). Coarse (10 m).
- **Approach 2 = STATE + TRANSFER:** detect Lantana by its *appearance* (GLCM texture + OBIA + NIR) in one
  high-res scene; signature transferred from high-res texture at reference-region GBIF points with matched
  negatives. Paid (Vantor 35 cm). Fine.
Two independent buckets pointing at the same patch = corroboration that substitutes for absent local
ground truth. That is the `INVASIVE_MAP_BENCHMARK` experiment.

## How this shows up in /why

`/why` groups an answer's steps by bucket and fills the template, e.g.:
> **CHANGE** · baseline: expected dry-season leaf drop · signal: stay-green cells · truth: transferred
> recent GBIF [20–40 km away] · confidence: gate 0.82, MODELLED not observed · [high-res confirm pending]

So a reader sees not just *what data* but *what kind of inference* produced the answer, and where its
uncertainty lives. When we add a skill, we add its bucket's template — `/why` stays coherent as we grow.

## Rule for new skills/tools

1. State the bucket(s) it serves (add a new bucket only if genuinely new — don't cram).
2. Give its /why one-liner (baseline/signal/source/confidence).
3. If it uses TRANSFER, it must surface the gate + "modelled not observed" + a data-ask.
