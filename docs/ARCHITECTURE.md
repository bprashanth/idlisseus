# Idlisseus — Architecture & State

Last updated: 2026-06-28

## What this is

Idlisseus is a self-hosted AI stack for NGO teams, running on a DGX Spark GB10
(121 GB unified memory). It combines a capable LLM backend with a full-featured
web UI for chatbot and agentic data science workflows.

## Current production model

**Qwen3-Next-80B FP8** (`~/models/Qwen3-Next-80B-FP8/`, 77 GB, 8 shards)
- vLLM container `qwen80b-vllm`, bound to `172.17.0.1:8001`
- ~3-20s per response (fast enough for real-time chat)
- Hermes tool-call format (`--tool-call-parser hermes`)
- 110 Gi RAM at steady state — leaves 11 Gi headroom
- Startup: ~9 minutes cold load from EXT4

Start: `docker start qwen80b-vllm` (or `deploy/qwen80b/run.sh` once created)
Stop: `docker stop qwen80b-vllm`

## Historical / available models

| Model | Path | Size | Notes |
|-------|------|------|-------|
| DeepSeek V4 Flash (ds4) | systemd service `ds4-ssd` | 670B, SSD stream | 121-189s/turn; use for deep reasoning |
| Seed-OSS-36B AWQ | `~/models/Seed-OSS-36B-AWQ/` | 21 GB | vLLM port 8001, reasoning parser |
| Qwen3.5-2B (sidekick) | `~/.cache/huggingface/hub/models--Qwen--Qwen3.5-2B/` | 4.3 GB | 4-5s/turn, low RAM |

ds4 MUST bind to `172.17.0.1` (Docker bridge), NOT `127.0.0.1` or `0.0.0.0`.
ds4 + Qwen3-Next-80B cannot coexist (both need near full 121 Gi RAM).
ds4 + Seed-OSS-36B CAN coexist at steady state (~117 Gi), but NOT during
ds4 warmup (spikes >83 Gi briefly) — always run ds4 smoke first, then start Seed.

## UI: Idlisseus (rebranded Odysseus)

Source: `idlisseus/odysseus/`
Docker compose: `idlisseus/odysseus/docker-compose.yml`
Start: `cd odysseus && docker compose up -d`
Port: 127.0.0.1:7000 (local) → Cloudflare Tunnel (public)

**Multi-user**: yes — login/signup routes in `routes/auth_routes.py`.
Users authenticate via Odysseus login, network gated by Cloudflare Access.

**Agent mode** (`set_mode agent` in UI):
- Fenced code block execution: ```python```, ```bash```, ```web_search```, etc.
- Runs server-side in the Odysseus container
- Available tools: bash, python, web_search, web_fetch, trigger_research,
  read_file, write_file, edit_file, grep, glob, create_document,
  chat_with_model, manage_memory, generate_image, manage_calendar, etc.
- Does NOT require Hermes format — model writes fenced blocks, Odysseus executes
- HTML documents created by agent render as iframe preview (interactive JS works)

## Public access

Cloudflare Tunnel → `cloudflared` on Spark → Odysseus :7000
Cloudflare Access gates by email/domain (no VPN needed on client side).
TLS terminated by Cloudflare — HTTPS by default.

For IDE extensions (Cline, etc.): point at `https://your-tunnel-url/v1`
Model ID: `qwen3-80b`, API key: any non-empty string.

## Spiral fix (anti-hallucination)

### Root cause
`agent_max_tool_calls = 0` (unlimited) + multiple tool blocks per round =
unbounded web_search loops. 50 "rounds" ≠ 50 tool calls.

### Level 2 fix (settings.py)
`agent_max_tool_calls` default: 20 (hard ceiling on total tool calls per turn)

### Level 2b fix (agent_loop.py)
web_search-specific cap: max 5 per turn, dedup by query string.

### Level 3 fix (two-stage research flow)
For research/citation requests: agent drafts answer first with [UNVERIFIED]
markers, then does ONE search per marker. Not yet implemented — planned.

## Data science workflow (target)

User uploads CSV → Odysseus agent mode → python tool processes server-side →
`create_document` HTML → rendered in iframe preview panel in browser.
Chart.js / interactive JS works in the iframe (full browser context, no sandbox).

## Key constraints (security)

- Never expose ds4/vLLM ports publicly (only via 172.17.0.1, not 0.0.0.0)
- No cloud API keys on this machine
- Do not `sudo reboot` unattended
- Cloudflare Tunnel: do not expose without HTTPS
- No real NGO passwords in code

## Benchmark results (2026-06-27)

Chatbot benchmark: 3-turn conversation on invasive plants / restoration ecology.

| Config | Avg turn time | Concurrent 2 users (wall) | Quality |
|--------|--------------|--------------------------|---------|
| ds4 alone | 121s | 157s (serial queue) | Best depth |
| ds4 + sidekick | 121s / 11s | 102s (parallel) | Mixed |
| Qwen3-Next-80B alone | 8s | 3s (batched) | Excellent |

80B Qwen is the clear choice for chatbot. ds4 reserved for deep reasoning tasks.

## Next steps

- [ ] Cloudflare Tunnel setup (waiting for user token)
- [ ] Level 3 two-stage research harness in chat_routes.py
- [ ] Test end-to-end: CSV upload → agent → interactive dashboard in browser
- [ ] IDE journey: Cline + Antigravity/Eigent pointing at tunnel URL
- [ ] MCP integration (future)
