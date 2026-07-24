# Eastern Ghats run — Round 1 report

**Question:** does the PLAYBOOK/skills/connectors **refactor** (thin router + progressive-disclosure
recipes) + **L1** (name resolution) + **L2** ("where"→map) improve answers, speed, efficiency — on a
NEW, researcher-grade curriculum (Eastern Ghats snakes/spiders: distribution, phylogenetics, stable
isotopes, cave taxa, conservation, taxonomy)? And: **what does a better PLANNER buy?** (3 threads.)

Syllabus: 16 cursor-generated questions (`syllabus.json`). Round 1 = a 6-question subset `[0,4,7,10,12,14]`
spanning all six categories. Threads: **deepseek** (v4-flash), **glm** (5.2), **hybrid** (glm plans →
deepseek executes). Metrics mined from `state.db` (`eg_bench.py`): per-question cost/tools/api + 6 signal
flags. Score = fraction passing each signal.

## Aggregate (6 Q each)

| thread | mean sec | mean tools | mean cost$ | papers_first | name_resolved | map_for_where | honest | grounded | not_empty |
|---|---|---|---|---|---|---|---|---|---|
| deepseek | 506 | 58.5 | **0.067** | 1.00 | 0.67 | 1.00 | 1.00 | 1.00 | 1.00 |
| glm | 472 | **36.5** | 0.233 | 0.83 | **0.83** | 1.00 | 1.00 | 1.00 | 1.00 |
| hybrid | **671** | 66.7 | 0.074 | 1.00 | 0.83 | 1.00 | 0.83 | 1.00 | 1.00 |

## Findings

**1. The refactor works — answers are researcher-grade across ALL models.** Every thread resolves species
names, checks papers/literature, produces honest, grounded answers, and never returns empty. Examples:
the green-cat-snake fabrication is gone; deepseek correctly states the specific COI+RAG1 phylogeny "does
not exist in published literature" and cites Mallik et al. 2020 (Zootaxa 4874, DOI); glm gives correct
IUCN NT + WPA Schedule I for *Python molurus*, distinguishing *P. bivittatus*. **The skill/router is the
moat — quality is similar across models** (echoes the earlier model×skill finding).

**2. A better PLANNER buys almost nothing here — it's the RUNNER that's the bottleneck.** The hybrid
(glm-plans → deepseek-executes) is the **slowest** (671s — two sequential calls) and has the **highest
tool count** (66.7). The glm plan did **not** reduce deepseek's over-exploration: Q4 phylogenetics
over-ran in both deepseek-alone and hybrid; Q7 went 16→52 tools *with* the plan. Over-exploration is a
runner-execution trait a plan can't constrain. Verdict: **skip the hybrid planner** — it adds latency
without efficiency or quality gain. (glm-alone is what you'd reach for when you want the strong model.)

**3. The efficiency problem is real and unsolved by the refactor: tool discipline.** The router says
"~3–5 tools then answer", but every model runs **36–67**. Some of that is legitimate (these are
multi-species × multi-method questions), but the variance is the tell: glm answered the phylo question in
**9 tools / 202 s**; deepseek took **65 tools / >13 min** for the same question. The refactor fixed
*routing/correctness*, NOT *tool discipline*. **This is the next iteration's target** (esp. literature
questions grinding satellite/occurrence connectors they don't need).

**4. Cost vs. quality:** deepseek ≈ **3.5× cheaper** than glm at similar answer quality, but slower and
less disciplined (58 vs 36 tools). glm is the most efficient *per answer* (fewest tools, best
name-resolution) but pricey. Hybrid inherits deepseek's cost but not glm's discipline → **worst on speed**.

**5. Nuance — "papers_first" measures TOOL use, not literature-grounding.** glm answers phylo/taxonomy
from its **weights** (cites real papers: Mallik 2020, Mohapatra 2017 *A. anomala* from Odisha) *without*
calling `paper_data` (so papers=0.83). The model already knows the herp literature. **Implication for the
researcher-audience goal:** our `paper_data` corpus wins only where it holds data the model lacks —
**dataset-embedded presence points**, obscure regional records, unpublished-but-archived tables. That is
exactly what "beat their lit review" must lean on; citing famous papers isn't enough.

**6. Harness note:** the 780 s "timeout" is a *measurement* artifact — the hermes session finishes after
the harness stops waiting; re-mining `state.db` recovered the completed answers. So "timeout" here means
"very slow", not "failed".

## What to change next (mining → improvements)
- **Enforce tool discipline** (the #1 lever). Strengthen the router's budget into a concrete STOP rule,
  and route **literature-shaped questions** (taxonomy / phylogeny / conservation-status / diet-isotopes)
  to lead with `paper_data` + knowledge and STOP — not grind satellite/occurrence grids. Test: does the
  over-explorer (deepseek) drop tool-count on Q4/Q12 after the fix?
- **Lean the paper corpus toward dataset-embedded points** (per finding 5) so it beats parametric recall.
- **Drop the hybrid planner** from the default; use glm-alone when you want the strong model.

## Round 2 — the tool-discipline fix (deepseek re-run on Q4, Q12)
Applied a concrete STOP rule (router) + "literature questions don't grind satellite connectors"
(papers-first recipe), re-ran the two questions deepseek ground hardest on:

| Q | tools (r1→r2) | sec | cost$ | signals |
|---|---|---|---|---|
| Q4 phylogenetics | 72 → **59** (−18%) | 780→752 | .129→.102 | 3/4 → **4/4** |
| Q12 conservation | 87 → **66** (−24%) | 551→511 | .071→.050 | 4/4 |

**Verdict:** prompt-strengthening trims over-exploration **~20%** and improved Q4 quality — but they're
still ~60 tools, an order of magnitude over the ~6 budget. **Prompt-only cannot enforce tool discipline;
this is structural.** The real fix is a *mechanism*: a hard `--max-turns` cap tuned per question-type, or
a mid-run hook that injects "you've used N tools — wrap up and answer now" at a threshold. (Next.)

## The planner-value answer (deepseek vs deepseek+glm-5.2) — matched 6 Q

| metric | deepseek | deepseek+glm (hybrid) | delta |
|---|---|---|---|
| wall sec | 506 | 671 | **+33%** |
| tools | 58.5 | 66.7 | +14% |
| cost $ | 0.067 | 0.074 | +11% |
| **quality** (signal pass-rate) | **0.92** | **0.92** | **0** |

**Adding the glm-5.2 planner makes deepseek 33% slower, 14% more tool-heavy, 11% costlier — for ZERO
quality gain.** Why: the refactor already lifts the *cheap* runner to 0.92 quality, so there's no headroom
for a planner to add; and over-exploration is a runner trait the upfront plan doesn't curb (it adds work).
**The skill/router is the moat — a cheap runner + the good skill ≈ a strong runner + the good skill, at
~3.5× less cost than glm-alone and without the planner's latency tax. Don't use the hybrid planner.**

## New capability — `litscout` (author co-authorship-graph paper/dataset discovery)
Built + wired (per the "walk the people" ask): `litscout.py` over **OpenAlex** (free). `authors <topic>` →
the co-authorship cluster (for shieldtail snakes: real cluster S.R. Ganesh, Bhupathy, Gower); `expand
--author <seed> --topic <t>` → co-authors + their **archived datasets** (DOIs) → bridge to
`paper_data.extract` for the **presence points inside**. This is the researcher-beating step a title
search misses; folded into `recipes/papers-first.md`. Chain: author → co-authors → topic → datasets → points.

