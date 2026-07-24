# Multi-turn + the smart/less-smart split (2026-07-09)

Realistic chat matters: users never ask a clean one-shot question and want a reply in ~1 min. Built a
**multi-turn harness** (`mt_bench.py`): a cheap user-simulator (OpenRouter, hidden goal, terse, says DONE
when helped) vs the agent on **qwen122b**, continued via hermes `--resume`. Scored the *constitution
behaviors*, not just content.

## qwen122b multi-turn (4 scenarios) — the constitution does NOT hold on the cheap model
- `clarified 0/4` — it **never asks**; it assumes species+scope and dives in.
- `short 1/4` — thesis answers.
- `transfer + flag-modelled 3/4` — this invariant *does* hold.
- **mean 1.2 turns** — it front-loads everything, collapsing the conversation to one shot (the sim says
  DONE because it got a wall of answer). The opposite of "short answer → the right follow-up."

Prose can't enforce ask-first / brevity — now confirmed for the interactive case too (matches the
one-shot bench's tool-discipline finding).

## Top-3 smart/less-smart positionings (glm-5.2 at the edges of free qwen) vs qwen-alone

| use | qwen-alone | + smart (glm) | cost of the smart step |
|---|---|---|---|
| **1. CLARIFY-GATE** (ask-vs-proceed, front) | 0/4 clarify | **4/4 clarify** | ~137 tok, tool-less |
| **2. SYNTHESIZER** (short answer, back) | mean 1737 ch, short 1/4 | mean **614 ch, short 4/4** | ~600 tok, tool-less |
| **3. VERIFIER** (post-check) | — | 4/4 caught | small; redundant w/ a length cap for "short" |

The gate produces exactly the right question every time — *which + why*:
> "Which invasives—plants like Lantana, or others—and what's your goal, mapping spread or impact on
> elephant habitat?" · "Which species are you after, and what are you trying to understand — distribution,
> venom risk, or prey ecology?"

The synthesizer turns qwen's 1737-char dump into a short, **modelled-flagged** answer:
> "Modelled result (RF + phenology, trained on 12 corridor records, not site-specific): 37/784 cells ≥0.5,
> max 0.59. Zero confirmed inside the 70-acre site — a transferred signal at 10 m, small patches may be
> missed. Top waypoint 12.73847, 78.18152…"

## Verdict — smart at the EDGES, cheap in the MIDDLE
Put the smart model on **clarify (in)** and **synthesize (out)**; keep the cheap local model on the
**tool-grinding middle**. This is the *opposite* of the failed hybrid (smart-planner → dumb-runner, +33%
latency / 0 quality) — that put smart in the middle (planning execution), which doesn't help because
execution *discipline* isn't a planning problem. Both smart calls here are tiny (tool-less, ~137–600 tok)
while the expensive tool grind stays free on qwen. So the smart tax is ~cents/turn, not a doubled run.

## Proposed shape for TONIGHT'S experiment — "smart bookends, cheap middle" + mechanism control
Per turn:
1. **Smart clarify-gate** (glm, ~137 tok): vague/broad → ask "which + why"; clear → a tight directive.
2. **Cheap qwen** runs the connectors (free/local), under a **mechanism tool cap** (the prompt-only fix
   trimmed only ~20% — this needs a hard cap / a mid-run "wrap up now" hook, not more prose).
3. **Smart synthesizer** (glm, ~600 tok): short answer + 1–3 follow-ups, modelled-flagged. (Tune the
   prompt: it nailed brevity but offered follow-ups 0/4 — add an explicit "end with 1-3 options" rule.)

Measure the assembled loop vs qwen-alone and glm-alone on the multi-turn behaviors + cost/turn. And guard
every behavior with the **golden-trace suite** so it stops regressing (`dss/ARCHITECTURE.md` §5, §7).

Open question for the design: is the clarify-gate a *model* call or can a cheap classifier + a template do
it? (4/4 with a tiny glm call is cheap enough that a model is probably fine — but worth an ablation.)
