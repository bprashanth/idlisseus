# Agents

Agentic inference on this stack: the model executes tool calls in a loop,
tools run server-side, and the results feed back into the next LLM call.

## Architecture

Two agent harnesses have been tested:

**Hermes (token proxy)** — `agents/hermes/`
- Runs as a sidecar container; inserts a `<tool_call>` prefix token into the model's output stream
- Forces the underlying model (any OpenAI-compatible endpoint) to emit Hermes-format tool calls
- Trade-off: extremely model-agnostic (works with ds4, Seed-OSS, any model) but is a hack — it
  intercepts the raw token stream, not a clean API. Brittle under model updates.
- Use when: you need tool calls from a model that doesn't support them natively

**Idlisseus agent loop** — `chatbots/odysseus/src/agent_loop.py`
- Native Python loop: stream model output, detect fenced code tool blocks, execute, feed results back
- No token proxy needed — 80B supports Hermes tool-call format natively via vLLM's built-in parser
- Tool budget: 5 web searches per turn, 20 total tool calls per turn (prevents spirals)
- Tools: `bash`, `python`, `web_search`, `web_fetch`, `trigger_research`, `read_file`, `write_file`,
  `create_document`
- Use when: you want a supported, maintained loop with safety guardrails

## Security model

Agent code runs inside the Idlisseus Docker container. The container has:
- Network access (web_search hits SearXNG, web_fetch hits the open internet)
- Filesystem access limited to the container's `/app/` tree (not the host)
- No GPU pass-through (the container is CPU-only; the model is on the host via 172.17.0.1)
- No cloud API keys configured

`bash` and `python` tools execute in the container's namespace. A user with chat access can
run arbitrary code inside the container. This is intentional for a single-team deployment —
do not expose to untrusted users without a sandbox layer (e.g. gVisor, Firecracker).

## Spiral prevention

Without limits, an agent can loop indefinitely on web_search (observed: 50+ tool calls in one
turn). Mitigations in place:
- `MAX_AGENT_ROUNDS = 50` — hard round limit
- `agent_max_tool_calls = 20` — total tool calls across all rounds per session turn
- `_WEB_SEARCH_CAP = 5` — web_search calls per turn
- Duplicate query detection — same query (first 200 chars) skipped with explanation message

## What agents can and cannot do today

Can:
- Process uploaded CSV files with Python, generate HTML dashboards (rendered as iframes)
- Search the web for recent information, fetch and summarize pages
- Create documents that persist in the user's document library
- Run shell commands and Python scripts inside the container

Cannot:
- Open a browser on the host (no display, no Playwright/Selenium installed)
- Install persistent packages (container resets on rebuild)
- Access files outside `/app/` in the container
- Reach the model's vLLM API from within — tool calls go back to the same session server, not a new LLM call

## Hermes architecture details

See `agents/hermes/` for Dockerfile, token proxy code, and systemd service.
The proxy intercepts the `/v1/chat/completions` stream at the token level, checks for the
Hermes tool-call sentinel token, and rewrites the response into OpenAI tool-call format.

## Hermes connectors (Earth Engine) + the uv-cache fix

For the semantic-broker experiments (`benchmarks/semantic_broker/`), Hermes is given
live data connectors. **Earth Engine is wired and verified end-to-end in a real agent
run** (FIRMS/MODIS fire, ESA WorldCover, SRTM, WDPA; project `plantwars`). Three
non-obvious requirements — each cost a debugging cycle:

1. **Preinstall `earthengine-api` + `pymupdf` in the image.** The agent's `import ee`
   fails at runtime because auto-install-on-import can't map the import name `ee` to the
   pip package `earthengine-api` (same for `fitz`→`pymupdf`). Baked into the Dockerfile.
   This also fixes the Odisha-run pymupdf failure — in-agent PDF parsing now works.
2. **Creds go at the sandbox HOME, `/opt/data/home`.** `execute_code` runs scripts in a
   sandbox whose `HOME` is `{HERMES_HOME}/home` (`get_subprocess_home`), **not**
   `/opt/data`. So EE creds must be at `~/.hermes/home/.config/earthengine/credentials`
   (owned uid 10000). Staging at `~/.hermes/.config` does nothing.
3. **`~/.hermes` owned by uid 10000** (the agent runs as 10000, not root — `main-hermes`
   drops privileges; the mount root must be traversable by 10000), and image
   `ENV HOME=/opt/data`.

The canonical invocation + full preconditions live in
`benchmarks/semantic_broker/run_v-1.sh` and `CONNECTORS.md`.
