# Chatbots

The primary chatbot deployment is Idli Insights (formerly Idlisseus/Odysseus) in `chatbots/odysseus/`.

## Idli Insights features

**Conversation**
- Multi-user with per-user chat history and settings
- Session persistence (SQLite, `data/app.db`)
- Agent mode: model executes tool calls in a loop (see `../agents/`)
- Streaming responses with per-token SSE

**Document library**
- `create_document` tool saves model output as named documents
- HTML documents render as interactive iframes (Chart.js, vanilla JS work)
- Plain text, markdown, JSON render in a code panel with copy/download

**Visual stage (idli-result/1) — new**
- Visual-first conversation mode: full-viewport "stage" of scrollable chapters, one per question
- Generic renderers driven by the `idli-result/1` contract (`dss/VISUAL_RESULT_CONTRACT.md`):
  SVG figure maps (AOI/cells/points/modelled surfaces), time series with coverage strips,
  stat tiles, hierarchy bars, dashboards of result cards — no sector vocabulary in the UI
- Evidence-class design system (validated palette): observed/derived/modelled hues;
  proxy dashed, designed diamonds, reported outline, missing hatched
- Hover tooltips, click-through drill-down to source rows, provenance/audit panel,
  capability-derived action chips, synthetic-data ribbon, partial/failed states
- Transport: `<!-- idli-result:{...} -->` markers in the chat stream + `/api/visual/*` proxy
  (`routes/visual_routes.py`); ambient site-orientation on visual-capable endpoints
- Dev: `static/visual-lab.html` renders the contract fixtures (`static/contracts/fixtures/`)
  with zero backends; code in `static/js/visual/`

**Web / research**
- `web_search` via self-hosted SearXNG (no external search API key)
- Numbered citation panel: sources extracted from tool output and displayed
- Model instructed to cite by [1][2] numbers matching the panel

**Memory**
- Per-user memory file, loaded into system prompt context
- User can view, edit, and clear memory from settings panel

**Calendar / Notes / Cookbook / Email**
- Integrated sidebars; Calendar uses external `.ics` feeds
- These are Odysseus upstream features; see `docs/odysseus.md` for full list

## Producer-consumer exchange (latest dispositions)

- TR-VIS-0003 **implemented**: model-selected subject membership renders as a "read as"
  disclosure (dashed rule + explicit "assistant interpretation" wording) on cards and in
  the panel caption; `correct-subject-*` actions render as "Change this reading".
  Fixture: `dss/contracts/fixtures/11-model-selected-subject.json`.
- TR-VIS-0004 **accepted**: blocked lookups render no successful visual; selection turns
  show progress; asked the producer to emit clarification candidates as guided actions
  for chip-level rendering.
- TR-VIS-0005 **implemented**: "Report a problem" on every result card (prominent on
  failed/blocked/error results) → description form (transcript inclusion on by default,
  visible messages only) → full public preview with repository + warning → explicit
  publish confirmation. Proxy: `/api/visual/{endpoint_id}/feedback/draft|submit`.

## Citation status

Currently **Level 1** — prompt-only:
- Model sees a numbered source list in its tool output context
- Instructed to write `[1]`, `[2]` inline matching those numbers
- No automated verification that claims match sources

**Level 3 (planned, not built):** two-pass research mode:
- Pass 1: draft with `[UNVERIFIED]` markers on all factual claims
- Pass 2: bounded web searches per claim → cite or mark `[COULD NOT VERIFY]`
- Opt-in toggle ("Research mode") to avoid latency overhead for casual queries
- See `docs/two-stage-verification.md` for design

## What agents can render in the UI

The document panel renders:
- Static HTML (tables, lists, styled text)
- Interactive HTML (Chart.js charts, click handlers, form inputs, local JS)
- The iframe sandbox allows scripts and same-origin access, so Chart.js loaded from CDN works

This makes the data-science workflow viable: agent generates an HTML dashboard → renders live
in the same conversation, user can interact with charts without leaving the chat.

## Internal architecture notes

See [`docs/odysseus-internals.md`](docs/odysseus-internals.md) for:
- How "recalled" memory works (BM25 + vector, per-user isolation caveat, no auto-clear)
- Deep research loop terminal conditions and where images come from
- Explain Simpler / rewrite endpoint (NOT a chat resend — separate lightweight call)
- Agent mode vs Hermes: what's active, what's redundant

## Running Idli Insights

```bash
cd chatbots/odysseus
docker compose up -d

# After code/static changes:
docker compose build odysseus && docker compose up -d --force-recreate odysseus
```

Access: https://chat.idli.cc (Cloudflare Tunnel + Cloudflare Access email gate)

### Visual shell — "Field journal" (2026-07-27)

The product is branded **Idli Insights** (display only; `idli-insight-*` routing
ids are unchanged), with an idli mark — steamed disc, three steam wisps — as the
favicon and logo. The whole product — login, shell, chat, cards, charts, maps,
panels — runs on
one design system (`dss/DESIGN_SYSTEM.md`): warm paper page, white cards, ink
type, a single pine-green accent, and an amber marker wash behind the key figures
in an answer (capped at three, text nodes only, never inside code/links/tables).
Display type is a vendored Source Serif 4 (landing hero, site names, figure
headlines, stat values); UI is Inter; mono is reserved for identifiers. Charts
keep the validated evidence-class palette — the shell sets a light root `--bg`,
so the renderers pick their light steps automatically (aqua is sub-3:1 on this
surface; the relief rule is satisfied by legends + row tables on every card).

A dark mode (nav Theme toggle, persisted) re-steps the same family for night:
`#16140f` page, mint-pine `#5db390` accent, `--pine-fill` keeping solid buttons
readable; charts flip to their validated dark palette automatically. The chat
thinking indicator is an otter strolling off with paw prints, in the UI face.

Shell: a 232px nav rail (Chat / Maps / Data / Sites / Theme + pine "New
analysis" and a quiet Sign out) with active states; the stock sidebar slide-over
is retired (History removed — the app always opens on the site-selection page,
and the current conversation is one Chat click away); the
right context rail (site stat tiles, data streams, recent visuals) is back; the
data explorer and the figure panel are mutually exclusive right-hand surfaces,
and the composer shifts with whichever is open. Machine voice is gone from the
reading line: role labels say "Idli Insights" (never `idli-insight-*`), session
titles are prettified to the site name, the Why panel ("How this was answered")
defaults closed and replaces tracebacks with a plain sentence, and card kind
labels are human words ("Map", "Time series"). Login is deterministic brand
chrome (no theme/bg-effect bootstrap) matching the app.
