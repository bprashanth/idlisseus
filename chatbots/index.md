# Chatbots

The primary chatbot deployment is Idli Insights (formerly Idlisseus/Odysseus) in `chatbots/odysseus/`.

## Idli Insights features

**Conversation**
- The composer is one line: a `>` prompt, what you type, and an attach button
  (with send appearing beside it once there is text). Shell access is never
  offered (there is nothing behind it to reach), web search belongs to the site
  pack, and the empty-state "+" duplicated the rail's New analysis button. The
  placeholder is "ready when you are…".
- Multi-user with per-user chat history and settings
- Session persistence (SQLite, `data/app.db`)
- A plain visit lands on the **site-selection** page; a refresh mid-conversation
  (a `#<session-id>` URL) returns to that conversation. Clicking the brand mark
  also opens site selection. History and in-app session navigation reopen
  persisted conversations.
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

## Atlas — the pack as a living constellation (IDL-REQ-0003, 2026-07-28)

The Data nav opens on the whole graph: the producer's bounded ambient sample
(~180 nodes / ~525 edges in the fixture) rendered as a force-settled
constellation — dots sized by records, kind-toned and named in the legend,
pine filaments solid for recorded relationships and dashed for derived ones.
Landmarks (the heaviest nodes) stay labelled with collision declutter;
everything else names itself on hover, which also lights its filaments and
dims the rest. Drag to pan, scroll to zoom, drag a dot to nudge it; the view
auto-fits until the person takes over. Search covers every node kind and
alias; choosing a result anchors it (pine, size floor, pinned centre) and
expands its bounded neighbourhood — merges by stable id, three hops before
re-anchoring, budgets and omissions visible. Click opens a glass detail card
(backdrop blur): counted relations grouped by producer relation and basis,
provenance, and capability actions that fill the composer without sending.
The physics is presentation only — positions carry no meaning beyond
adjacency — and prefers-reduced-motion settles instantly. Live from
`/v1/graph*` when Codex ships; the sector-neutral fixtures render as a
labelled sample until then.

## Themes centre — recurring questions and published answers (IDL-REQ-0004, 2026-08-01)

People arrive with a question, not with a wish to see maps, and the questions
repeat. The **Themes** nav opens those recurring questions (from the producer's
catalogue, `GET /v1/decision-maps` via `/api/visual/{endpoint_id}/decision-maps`)
with what has been published to answer each one. A theme leads with the question
itself; the other phrasings it absorbs sit under it as evidence that it recurs.
An **answered** theme opens its published analysis; an **open question** lists
the exact `required_inputs` still missing and offers no answer affordance, so
the centre can never imply an answer exists. A theme can be taken into the reader's own conversation, never auto-sent. From
the index only the question travels (nothing has been run yet); from a reading
view **the answer itself does** — the map renders inline from its
`idli-result` marker, and a briefing of the facts behind it (recipe and
version, how the estimate is made, the test and its checks, the data sets with
DOIs, whose basemap, the stated limits) is added to the transcript and
persisted, so the next turn's model can answer "what model was used?" or
"where did the data come from?" from the record. The composer opens naming the
analysis: the assistant resolves a visual by identifier rather than by
re-reading the transcript, so an unanchored "this" only earns "which visual do
you mean?" — the anchor is visible, editable and deletable, and the reader
writes their question after it.

The reading view is the pack's **published field note** (TR-VIS-0010) where one
exists: the short answer, the map, a prominent "What to do now" with numbered
steps, a "Where" index — the instruction said once, then the location ids as chips
that find their feature on the map when clicked (no recompute, no value
changed), then what was measured, the named
estimator, the test in plain language, and "Why we are not giving stronger
advice". Credit and publication date head it; contributors appear only when
supplied. The technical audit — "How this map was tested" and full provenance —
stays available after the article, and the note is bound to the arguments it
was written about, so a rerun never inherits it. Packs without an article keep
the old assembled write-up.

**Catalogue readiness is not validation** (TR-VIS-0009): `partial` themes run
too, labelled "Evidence, not yet an answer". Features flagged by
`validation_priority_field` are drawn as a dashed collar — never the solid one
a passed selection earns — and named in words both in the tooltip and in a key
under the map: "check or collect evidence here — not a recommendation". They
survive a failed or pending test, because they are what would settle it. Where the producer publishes nothing the consumer shows
less rather than inventing — no mined counts, no leaderboard position and no
byline exist yet (all asked for in IDL-REQ-0004), and the write-up is assembled
from the pack's own declared sentences and **labelled as such**. An author's
declared basemap is honoured for that figure only (a known proxied id; an
unrecognised one degrades to the default, and tiles never leave the same-origin
proxy) without overwriting the reader's global preference.

Every decision map arrives with its test (TR-VIS-0008). "How this map was
tested" renders in the reading flow — under the map in a chat card, in the
panel caption right after the claim, and in the Themes article — never behind
the audit link or an accordion. It states the validation kind, split rule,
periods, sample sizes and each declared check as value-against-threshold, with
pass state as a word *and* a mark (`✓ met` / `✗ not met`), plus the producer's
bounded claim verbatim. Observations withheld for testing share the *observed*
evidence class with those used to fit, so they carry their own mark — a crossed
ring — in both the SVG and Leaflet renderers; a location flagged by the declared
`selected_field` wears a heavy ink collar ("chosen within the declared budget").
**A failed test keeps its evidence and loses its recommendation**:
`selectionAllowed()` gates on `answer.validation.status === 'passed'`, so nothing
can be styled as chosen without a pass, and the panel says plainly that no place
is marked for action. Layer toggles show and hide drawn marks only — no
recomputation, no producer values touched, validation never hidden. Fixtures
12–14 plus `decision-map-catalog.json` are real producer output with payloads
committed, so the visual lab renders the whole treatment with no backend running.

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
ids are unchanged). The mark is a **raven**, deliberately cryptic — it ships as
ink-as-alpha (`static/icons/raven.png`) and is painted with the theme ink via
CSS mask, so one asset serves the nav rail, the login page and the landing; the
favicon bakes the same ink on a rounded tile. `static/icons/raven-cloud.png` is
the same bird resolved out of ~1,150 scattered points — the form only appears
once there is enough of it. All three regenerate from the source drawing with
`odysseus/assets/make_brand.py`. The wordmark is solid display type (the
hand-lettered Caveat scrawl is retired). A first-paint script in `index.html`
applies the shell classes and holds the boot overlay until the shell boots (20s
fallback), and the stock icon rail is display:none under the shell — so a
(hard) refresh never flashes the stock theme or its chrome. The whole product — login, shell, chat, cards, charts, maps,
panels — runs on
one design system (`dss/DESIGN_SYSTEM.md`): warm paper page, white cards, ink
type, a single pine-green accent, and an amber marker wash behind the key figures
in an answer (capped at three, text nodes only, never inside code/links/tables).
Display type is a vendored Source Serif 4 (landing hero, site names, figure
headlines, stat values); UI is Inter; mono is reserved for identifiers. Charts
keep the validated evidence-class palette — the shell sets a light root `--bg`,
so the renderers pick their light steps automatically (aqua is sub-3:1 on this
surface; the relief rule is satisfied by legends + row tables on every card).

A dark mode (nav Theme toggle, persisted) re-steps the family for night as a
neutral charcoal (`#212329` page, `#2a2d34` surfaces — no blue cast), with the
accent turning to ember `#e2a05f`, the same family as the landing's lights;
charts flip to their validated dark palette automatically. Every
loading state — the page-load overlay and the chat thinking indicator — uses
the braille spinner loop (⠋⠙⠹… at 90 ms).

Shell: the landing is a **field of lights**. Every site pack is a warm glow on
an always-dark sky, and the reach of the glow is how much that pack holds —
one comparable measure across packs (the admitted record count from
site-orientation), because sizing one pack by persondays and another by bird
detections would be a lie. Position is composition, not geography, and the page
says so: no endpoint publishes pack coordinates yet (asked for in
IDL-REQ-0004). Inside each light are small motes, one per **person** credited with the data
behind that story. They vary in size and scatter irregularly so they read as
part of the same dust as the sky, and each carries its surname where one fits
without colliding or crossing the core — the full name and affiliation are a
hover away. Institutions credited alongside people are left out rather than
reduced to a meaningless "surname". The producer publishes each source's DOI but
not its authors (IDL-REQ-0004 asks for them), so the names are resolved from
the public registries that minted those DOIs through a cached, allowlisted
same-origin route (`/api/visual/doi-authors`) — a source that resolves to
nobody contributes nobody, because an invented name would be worse than a
missing one. No nav rail and a clean URL (the session layer cannot stamp
`#session-id` before the shell has decided the view, nor while the landing is
open — the URL's own hash is what survives a real mid-chat reload). The
232px nav rail (Themes / Chat / Data / History / Sites + pine "New analysis";
light-or-dark is a moon beside Sign out, not a sixth destination — two entries
named Theme read as the same thing twice. Themes wears an open book, Sites a
location pin) exists only inside a chosen site, where the
empty chat is blank — the composer placeholder carries the invitation, "Ask
me something about <site>" (per active site, surviving app.js's resize
rewrite via `window._idliComposerPlaceholder`). The right context rail is one
section, "Data streams": the streams the latest answer's envelope cites
(`audit.source_versions`, linking out when the producer provides a URL/DOI).
It clears the moment a new question is sent and refills from that answer's
envelope — a text-only answer leaves it honestly empty; stat tiles and
Recent visuals are gone. The chat meta strip is a single "Settings" button (no
title/count/caret) whose menu is Rename / Copy Chat / PDF. Scrollbars are
theme-colored everywhere; the scroll-to-bottom pill is off. The data explorer and the figure panel are mutually exclusive right-hand
surfaces, and the composer shifts with whichever is open. Machine voice is gone from the
reading line: role labels say "Idli Insights" (never `idli-insight-*`), session
titles are prettified to the site name, the Why panel ("How this was answered")
defaults closed and replaces tracebacks with a plain sentence, and card kind
labels are human words ("Map", "Time series"). Login is deterministic brand
chrome (no theme/bg-effect bootstrap) matching the app.
