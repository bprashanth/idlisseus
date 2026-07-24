# How the DSS came to be — the history, in the order it was discovered

This is the narrative spine: each phase solved one problem and, in doing so, surfaced the next. Read it to
understand *why* every architecture piece exists before touching it. The blow-by-blow doc/benchmark index is
`benchmarks/CONCEPT_MAP.md`; the current mental model is `ARCHITECTURE.md`; the north star is
`../benchmarks/algebra/MASTER_PLAN.md`. The generalized (non-ecological) mirror of this same architecture
lives in `../../heartwood/docs/architecture/memory/`.

## Phase 1 — Testing models, and finding the real wall (search)
The goal started small: give everyone on the team a ChatGPT of their own. We tried ds4, Seed-OSS, and qwen
behind two agent harnesses — **Hermes** (a token-proxy that plans and keeps an auditable `state.db`) and the
**Idlisseus/Odysseus loop** (fast, search→decide→stop-at-max-turns). On a hard wildfire search-and-summarise
task, Hermes planned better and was auditable; the Idlisseus loop was quicker but shallower. **The finding
that reframed everything: no matter the harness or model, the wall was *search* — finding the right papers.**
It split three ways: (1) the *engine* (Google blocks; SearXNG works), (2) the *connection* (the agent
re-discovered API/SSL/login tricks every time), (3) the *results* were whim-dependent (great from the first
3 docs, or a spiral on one SSL failure).

## Phase 2 — Testing retrieval: stop rebuilding connectors and relying on search
The fix: don't waste turns rebuilding access to well-known data sites, and don't lean on fickle search.
Instead — **a set of connectors for known sources; cache hits; index hits; fetch-on-demand and re-cache;
search both the index and the internet.** The pipeline shifted from *request → datasets → visualize* to
**request → choose known connectors → pass through the cache/index → visualize.** With the search wall gone,
two needs became visible: (1) a **semantic lookup** to map "invasives" → "weeds" → "lantana", and (2)
**map layers** for ecological usefulness beyond scatter-plot search.

## Phase 3 — Self-improvement: how do we discover *new* connectors and data?
With fixed connectors and a finite working set of datasets retrieved, the first problem was no longer search
— it was **growth**. How do we discover new connectors and datasets on our own? The design, in parts:
(1) an agent sets a **syllabus** — ~10 questions on a topic; (2) **score** the answers (ask the agent to
list the ideal data sources, then run the question and see if it pulls them; did it model the right answer,
find the points/papers?); (3) for low scores, **mine the Hermes traces** to see *why* (missing connector,
failed to call it, inadequate data); (4) for inadequate-data cases, run a **scout** for new papers; (5) new
sources needing API keys get **flagged for user review**. This grew the corpus **17 → 169 → 256** papers.

## Phase 4 — Data cards and semantic retrieval
While the corpus was small and questions easy, keyword search sufficed. As it grew, we needed **true
semantic search** — "snake" → "cobra" — and, harder, to find **variables buried inside datasets whose title
is about something else** (a paper on wildfire whose table holds invasive-presence records). That required
ingesting the **codebook itself** into a semantic index. A three-way experiment — (1) plain-text over cards,
(2) one LLM over all cards, (3) embeddings over cards — was won by **embeddings** (the one-prompt LLM
degrades as the corpus grows). We could now grow the corpus/syllabus organically AND find semantically what
the user meant. But a new problem stood exposed: **going from "I found 10 datasets" to "here is a meaningful,
verifiable synthesis of them."**

## Phase 5 — Algebra: when to run which model
Now we had paper data, maps, and models to run over points and maps — and the question became **when to run
the models.** "Help me visualize lantana" means what, in a data-poor landscape? Visualize the points — or if
there are none, say so and *do better*: infer from climate-similar squares (SDM) or satellite-similar
squares (RF). And real questions don't stop at "visualize": *is this plot improving? is A better than B? is
lantana around elephants?* Rather than rathole on the meaning of "better"/"around", or fabricate, we chose
to give a **best approximation with stated limits and a clarifying question.** "Is lantana around elephants"
is a **relational** operation (is X around Y); "is this plot improving" is aggregate-greenness-over-plot at
t1 vs t2, fit a slope. **We use the LLM to synthesise the algebra operations, then the algebra to test the
truth in the data.** The insight: *you cannot model the landscape with algebra, but you can model the
questions humans ask about the landscape with algebra.*

## Phase 6 — Verification and provenance
More advanced modelling demanded introspection (the failure mode of black-box tools is doing sophisticated
things they never explain). Two designs: (1) a **`/why`** view that breaks the last answer's thinking trace
into its specific algebra operations; (2) a **human-eyeball verification** skill that draws the distribution
on a map a person can check. Doing (2) taught us humans can only really verify **higher-resolution** maps —
which is what drove acquiring high-resolution satellite imagery.

## Phase 7 — Models, gates, and requesting data
Deeper verification revealed there are **multiple ways to visualize the same data**, and showing the *right*
analysis for the *right* question under the *right* conditions matters — sometimes a model output should
**NOT** be shown (climate doesn't match; too few points). Hence **gates**: if a precondition for an
extrapolation isn't met, don't run it. In parallel we explored **different models for the same question**
depending on whether conditions are similar or different — folded into the gate: if all models are
permissible, their **intersection** is a strong authenticity check; if not, **flag that we need more data to
run better models.**

## Phase 8 — Progressive disclosure and routing
Even with connectors, tools, and embeddings, there was **too much prose** — it turned into LLM whimsy. Even
with the algebra rules, the agent inconsistently called the right tools: it forgot papers as a source and
reached for a live iNaturalist search, forgot to ask for clarification, forgot to translate local ↔
scientific names. The fixes: (a) **a system of skills** — load tools and context by **progressive
disclosure**, structured so only the needed tools load at the needed time, each self-describing via
`--describe`; (b) **a model hierarchy** — call a bigger brain at strategic points the smaller model struggles
with. That raised: *where do we put the smart model?* **Smart at the edges, dumb in the middle** worked
(the cheap model does the grunt tool-calling). **Smart planning did not.** And between very-smart+mid
(glm-5.2 + qwen-122b) versus just-smart-all-around (deepseek-v4), **just-smart-all-around won.** The thing
qwen-122b specifically struggled with was **pushing back and asking for clarification.**

## Phase 9 — Discipline
Several response behaviors needed to be *disciplined*: (1) shorter answers that ask for clarification instead
of assuming; (2) a **turn/tool cap** followed by a nudge to summarise in the last turns; (3) more **parallel
tool calls** to finish within a time limit. We found these belong in **hooks/tools, not prose** — **brevity
enforced as a mechanism is more predictable than brevity requested of a smart model via markdown.** More
than that: a **regression suite** massively protects discipline. Benchmarks surface *areas to improve*;
**regressions protect against losing discipline while you implement those areas.** The lasting lesson: model
the **typical questions a place asks** (from its data, communities, and thematic problems) — and guard the
behaviors with golden traces.

---

### The settled findings this history produced (the verdicts, preserved)
1. The wall was never modelling — it was **search**, then **growth**, then **synthesis**, then **discipline**.
2. **Codebook-in-card** is the retrieval lever; embeddings beat keyword on paraphrased queries and beat a
   one-prompt-LLM at scale.
3. You **cannot model the landscape with algebra, but you can model the questions** about it — synthesise the
   ops with the LLM, test truth with the algebra.
4. **Gates** decide when a model may run; **agreement between permissible models** is the authenticity signal;
   otherwise **flag for more data.**
5. **Smart at the edges, cheap in the middle** — a planner buys nothing; discipline/state was the real gap.
6. **Discipline belongs in mechanisms (hooks), not prose**; a **regression suite protects discipline** while
   benchmarks drive improvement.
7. A capability is invisible until the always-on **constitution names it** (the discovery/rule-4 lesson).

*(For the piece-by-piece status of each of these in the live system — wired vs buried — see
`benchmarks/CONCEPT_MAP.md` Part 2/3.)*
