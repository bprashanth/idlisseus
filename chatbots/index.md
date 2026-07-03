# Chatbots

The primary chatbot deployment is Idlisseus (formerly Odysseus) in `chatbots/odysseus/`.

## Idlisseus features

**Conversation**
- Multi-user with per-user chat history and settings
- Session persistence (SQLite, `data/app.db`)
- Agent mode: model executes tool calls in a loop (see `../agents/`)
- Streaming responses with per-token SSE

**Document library**
- `create_document` tool saves model output as named documents
- HTML documents render as interactive iframes (Chart.js, vanilla JS work)
- Plain text, markdown, JSON render in a code panel with copy/download

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

## Running Idlisseus

```bash
cd chatbots/odysseus
docker compose up -d

# After code/static changes:
docker compose build odysseus && docker compose up -d --force-recreate odysseus
```

Access: https://chat.idli.cc (Cloudflare Tunnel + Cloudflare Access email gate)
