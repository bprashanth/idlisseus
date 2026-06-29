# Agents: ds4-agent vs Hermes Agent

Two different ways to get multi-step, tool-using behavior out of a model. They are not
interchangeable in scope — read this before assuming one can replace the other.

## ds4-agent: ships with ds4, only works with ds4

`ds4-agent` is a native C binary built alongside `ds4-server` (same `make cuda-spark` build,
see `ds4/README.md`). It loads its own copy of the model directly — **it does not talk to
`ds4-server` over HTTP**, so it cannot run while `ds4-server` is also loaded (same unified-memory
constraint as switching models in `models.md`; stop the server first).

```bash
sudo systemctl stop ds4
ds4/ds4-agent -m ds4/ds4flash.gguf --non-interactive --chdir <workdir> -p "<prompt>"
sudo systemctl start ds4   # when done
```

It has built-in tools: read/search/write/edit files, run bash, browse the web (Chrome-backed).
**It only works with DeepSeek V4 Flash/Pro** — there is no way to point it at Nemotron, Seed-OSS,
or anything else; it's a narrow, purpose-built agent for this one model family.

## Why Hermes was needed

Once the question became "is ds4-agent's tool-use harness itself good, or would *any* harness
look about this good with this model — and how does a *different* model behave with a real
agent harness," we needed something that could run with **any** OpenAI-compatible model, not
just ds4's. That's Hermes Agent (NousResearch) — `nousresearch/hermes-agent` on Docker Hub. It
connects to any server implementing `/v1/chat/completions`, has its own memory/skills system, and
was the only practical way to test Nemotron-3 and (if desired) Seed-OSS in an *agentic*, not just
single-shot, capacity.

Concretely, Hermes is what let us ask: "same model, different harness — does the harness matter?"
(Benchmark 2: yes, substantially — see below) and "same harness, different model — does the model
matter?" (also Benchmark 2: yes, Nemotron-3 failed where ds4 succeeded, but the harness ran
identically against both).

**Use Hermes only in CLI mode** (`docker run -it --rm ... nousresearch/hermes-agent`, no
`gateway` subcommand) — `gateway` mode is a persistent multi-platform messaging bridge
(Telegram/Discord/Slack/etc.) that's explicitly out of scope here.

**Use the local image for benchmarks, not the upstream one** — see "Custom image" below.

## Custom image (`agents/hermes/`)

The upstream `nousresearch/hermes-agent` image runs as uid 10000 (non-root) with no sudo.
The model cannot install system packages at runtime, and some CLI tools it commonly reaches
for (`jq`, `wget`) are missing.  This caused benchmark failures where the model gave up on
downloads after hitting missing-tool errors rather than finding workarounds.

`agents/hermes/Dockerfile` derives from the upstream image and adds:
- `jq` — JSON parsing at the shell; the model tries this immediately for API responses
- `wget` — alternative downloader to curl with different SSL defaults
- `sudo` + passwordless sudoers entry for uid 10000 — lets the model `apt-get install`
  additional tools at runtime if it discovers it needs them

```bash
# Build once (from repo root):
bash agents/hermes/build.sh

# Use in any docker run command — replace the image name:
#   was:  nousresearch/hermes-agent
#   now:  hermes-agent-local
docker run --rm -v ~/.hermes:/opt/data --network host hermes-agent-local chat -q "..."
```

The Dockerfile follows the pattern from Hermes's own docs: `USER root` to install, `USER hermes`
to restore, no ENTRYPOINT override (s6-overlay's `/init` must stay as entrypoint).

**When to rebuild:** only when adding new system-level tools.  Python packages don't belong
here — `execute_code` auto-installs them via `uv` on first `import`, no Dockerfile change needed.

---

## What the model can actually do inside the container

Understanding this prevents wasted tool calls and helps write a useful `environment_hint`.

**Shell (terminal tool)**
Runs as uid 10000 with sudo (in the local image).  Available: `bash`, `python3`, `curl`,
`wget`, `jq`, `git`, `uv`.  Not available unless installed at runtime: most other system tools.

**Python (execute_code tool, the 🐍 blocks in transcripts)**
Uses `uv` to create an isolated venv per session.  Any `import` of an uninstalled package
triggers `uv pip install` automatically — no explicit install step needed.  The venv persists
for the container's lifetime but is lost on container restart (it's in the container's writable
layer, not in `/opt/data`).

SSL note: `requests` (auto-installed by uv) uses `certifi`'s CA bundle
(`/opt/hermes/.venv/lib/.../certifi/cacert.pem`), which differs from the system CA bundle
(`/usr/lib/ssl/cert.pem`).  Some government and NGO sites have certificates that the system
bundle trusts but certifi does not.  Prefer `urllib.request` for robustness, or pass
`verify='/etc/ssl/certs/ca-certificates.crt'` to `requests.get()`.

**Browser (browser_navigate tool)**
Headless Chromium, bundled inside the image at
`/opt/hermes/.playwright/chromium_headless_shell-*/chrome-linux/headless_shell`.
Hermes finds it via the `AGENT_BROWSER_EXECUTABLE_PATH` env var set in the image — nothing
to configure.  With `--network host`, the browser process uses the host's network stack
directly (same routing, same DNS, same firewall rules as the host).  No port exposure needed.

Use it only for pages that require JavaScript rendering.  Every `browser_navigate` call returns
the full HTML of the page, which can be 50-200KB of tokens — filling context very fast.

**What to tell the model (environment_hint)**
The `environment_hint` field in `~/.hermes/config.yaml` is injected verbatim into every
system prompt.  Keep it factual and short — the model reads it before every tool call.

Current recommended value (update via `sudo python3 deploy/hermes/point_at_model.py` or
edit `~/.hermes/config.yaml` directly with sudo):

```
IMPORTANT: web_search and arxiv are NOT available. For HTTP access use curl/wget or
execute_code (Python). Prefer urllib.request over requests — requests uses its own CA bundle
(certifi) which misses some site certs; urllib uses system CAs. If requests SSL errors occur,
switch to urllib.request or pass verify='/etc/ssl/certs/ca-certificates.crt' to requests.get().
execute_code auto-installs Python packages via uv on first import. jq and wget are installed.
sudo apt-get install works if a system tool is missing. Use browser_navigate only for
JavaScript-rendered pages — it returns full HTML and fills context fast.
```

---

## Files each one uses

| | ds4-agent | Hermes Agent |
|---|---|---|
| Binary/image | `ds4/ds4-agent` (native) | `nousresearch/hermes-agent` (Docker) |
| Config | CLI flags only, no persistent config file | `~/.hermes/config.yaml` (persistent, survives across runs via the `-v ~/.hermes:/opt/data` bind mount) |
| Working dir | `--chdir <path>` flag, files land directly there | `~/.hermes/workspace/` by default, or wherever the model's tool calls `cd` to under `/opt/data/` |
| Session data | none (one-shot per invocation with `--non-interactive`) | `~/.hermes/sessions/`, resumable with `hermes --resume <id>` |
| Ownership | normal — runs as your shell user | **`~/.hermes` is owned by container UID 10000**, not your shell user — every read/write/`find`/`cp` against it needs `sudo`, and shell globs (`*`) need `sudo bash -c '...'` so the glob expands under sudo, not your own shell |

## Pointing Hermes at a different model

`~/.hermes/config.yaml`'s top-level `model:` block controls the primary model. Critically, there
are also **~14 separate `auxiliary.*` sub-tasks** (`web_extract`, `compression`, `vision`,
`skills_hub`, `curator`, etc.) that each default to `provider: auto` independently — if you only
edit the top-level block, those are left ambiguous about which backend they'd use. (In practice,
no cloud API keys exist anywhere on this box, so `auto` could never actually reach a different
paid backend — but pinning everything explicitly removes all doubt about what a run actually
used end to end, which matters when you're trying to attribute results to a specific model.)

Use the script, don't hand-edit:

```bash
sudo python3 deploy/hermes/point_at_model.py <model-name> <base-url>
# e.g.
sudo python3 deploy/hermes/point_at_model.py deepseek-v4-flash http://172.17.0.1:8000/v1
```

See `deploy/hermes/config.yaml.reference` for what the result looks like (a reference snippet,
not a drop-in file — the real config has hundreds of unrelated lines).

## Smoke-testing Hermes against a (new) model — the two-step GO/NO-GO gate

Always run this before trusting Hermes against a model you haven't used it with before:

```bash
# 1. Basic connectivity
docker run --rm -v ~/.hermes:/opt/data nousresearch/hermes-agent chat -q \
  "What is 2+2? Reply with just the number."

# 2. Tool-calling (the one that actually matters for agentic use)
docker run --rm -v ~/.hermes:/opt/data nousresearch/hermes-agent chat -q \
  "List the files in your current working directory."
```

Hermes has a hard requirement of **at least 64,000 tokens of context** or it refuses to start —
check `/v1/models`' `context_length` field before assuming a new model clears this bar. Tool-call
format compatibility is the other real risk: ds4 maps its native tool-call format to OpenAI's
automatically (no extra server flags needed); generic vLLM servers need
`--enable-auto-tool-choice --tool-call-parser <name>` matching the model (`qwen3_coder` for
Nemotron-3, `seed_oss` for Seed-OSS — check the model's own serving guide for the right parser
name; guessing wrong silently breaks tool calls, the model just emits them as plain text instead).

**If either smoke test fails or behaves oddly: stop and say so, don't quietly route around it.**
That was the standing instruction for every model trial in this repo, and it's the only way the
Nemotron-3 speculative-decoding collapse (Benchmark 2) and the Seed-OSS slow-thinking finding
(Benchmark 3) got caught instead of silently producing misleading comparisons.

## Security posture: Hermes is NOT a steady-state service

**Hermes Agent must be stopped between sessions.** Do not leave it running unattended.

Hermes is a general-purpose AI agent with:
- Arbitrary shell execution (bash tool, no sandboxing by default)
- Python package installation via `uv` (triggered automatically on `import`, no approval)
- System package installation via `sudo apt-get` (in the local `hermes-agent-local` image)
- File system write access across the entire `~/.hermes/` tree (mounted into the container)
- Network access without a domain allowlist
- The ability to write and persist new skills, hooks, and cron jobs into `~/.hermes/`

This attack surface is manageable when you are watching a session and can intervene, but it is
not safe to leave open. A rogue prompt, a compromised website the model browses, or an
adversarial document the model downloads could trigger harmful tool calls.

**Steady-state (what should be running when Hermes is idle):**
```
ds4      — systemd service, always on
proxy    — NOT running
Hermes   — NOT running (no container, no background process)
```

**Session startup (before launching a Hermes task):**
```bash
sudo systemctl start hermes-token-proxy
# Then launch the hermes container with docker run ... for the task
# Stay present or set a hard kill timer
```

**Session teardown (immediately after the task ends):**
```bash
# docker run --rm means the container removes itself on exit, but double-check:
docker ps | grep hermes
sudo systemctl stop hermes-token-proxy
```

**After any Hermes session, audit what it did:**
```bash
# New Python packages installed by the model?
sudo docker run --rm -v ~/.hermes:/opt/data nousresearch/hermes-agent \
  bash -c "pip list 2>/dev/null" | sort > /tmp/post_session_pip.txt
# diff against a known-good baseline

# New files created in ~/.hermes (skills, hooks, cron)?
sudo find ~/.hermes/skills ~/.hermes/hooks ~/.hermes/cron -newer <baseline_marker> 2>/dev/null

# New system packages?
dpkg --get-selections | sort > /tmp/post_session_dpkg.txt
# diff against a pre-session snapshot

# Any lingering background processes?
pgrep -af hermes
```

See `benchmark4_qwen_sidekick/post_benchmark_audit.sh` for the automated audit script used
after benchmark runs.

---

## Token-budget proxy (required for Qwen3-Next-80B)

Some models produce more tokens per character than Hermes's estimator assumes, causing context
overflow mid-session.  A thin proxy at `:8001` corrects `max_tokens` before forwarding to
vLLM.  Always route Hermes through the proxy (transparent passthrough for models without a
known correction):

```bash
# Point Hermes at the proxy, not at vLLM directly:
sudo python3 deploy/hermes/point_at_model.py <model> http://172.17.0.1:8001/v1
```

See `docs/hermes-token-proxy.md` for full documentation.

---

## What we learned from running both against the same model (ds4)

Benchmark 2, identical task, identical model:

| | Time | Friction |
|---|---:|---|
| raw `ds4-agent` | 25 min | zero tool-call timeouts |
| Hermes + ds4 | 79 min | ~12 tool-call timeout-denials out of (an undercounted) ~40+ |

The harness itself adds real, measurable overhead on top of model speed. See
`benchmark2_hermes/REPORT.md` for full detail, including a documented bug in our own monitoring
(a grep pattern undercounted Hermes's true tool-call volume by ~4-5x in one run) — flagged there
for transparency since any "tool call count" cited for a Hermes run elsewhere should be treated
as a probable undercount unless cross-checked against the session's own final summary line.
