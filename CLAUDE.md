# CLAUDE.md — idlisseus repo

## Repo structure

```
models/          per-model weights, run scripts, systemd services
agents/          agent harness code (hermes/ token proxy)
chatbots/        UI deployments (odysseus/ = Idlisseus)
benchmarks/      benchmark runs (benchmark1_ds4/ … benchmark7_qwen35/) + semantic_broker/ (active)
docs/            cross-cutting docs (access.md, ARCHITECTURE.md, etc.)
ds4/             ds4 C+CUDA source (its own git repo — gitignored in parent, do not move)
ds4-kv/          ds4 KV disk cache (runtime, gitignored)
```

## Current state / active work

- **Primary model is Qwen3.5-122B-A10B INT4+FP8** (`vllm-qwen35`, `172.17.0.1:8001`),
  not 80B. 80B is the fallback. See `models/qwen3.5-122b/`.
- **Active experiment: `benchmarks/semantic_broker/`** — going from a conservation
  question to an insight over an AOI. Read `semantic_broker/VISION.md` first. v-1
  (raw Hermes) is done; a connector/insights layer is built (`connectors/`); the
  larger experiment still needs **dataset cards** (the functions-vs-cards split is
  in VISION.md). Hermes vs Odysseus tradeoffs: see `agents/index.md`.
- Fresh-clone reproduction (what to download): `REPLICATION.md`.

## When you make changes

**Always update the relevant index.md.**
- Changed a model config? Update `models/index.md` and the model's `README.md`.
- Changed Idlisseus code? Update `chatbots/index.md` if the feature list changed.
- Ran a new benchmark? Add a row to `benchmarks/index.md`.
- Changed agent tools or limits? Update `agents/index.md`.

## Running Idlisseus

```bash
cd chatbots/odysseus
docker compose up -d

# After code/static changes (static files are baked into the image):
docker compose build odysseus && docker compose up -d --force-recreate odysseus
```

## Security constraints (non-negotiable)

- ds4 must bind to `172.17.0.1` (Docker bridge), NOT `127.0.0.1` or `0.0.0.0`
- 122B (and 80B fallback) vLLM binds to `172.17.0.1:8001` (Docker bridge), NOT public
- No cloud API keys on this box — no OpenAI key, no Anthropic key, no HF tokens needed
- Cloudflare Access is the security boundary — do not bypass or open alternative ports
- Never `sudo reboot` unattended; stop containers cleanly first
- `SECURE_COOKIES=true` must stay set in `chatbots/odysseus/.env`

## Model switching

122B / 80B / ds4 each need the full 121 Gi pool — only one at a time:
```bash
# Primary: 122B
docker start vllm-qwen35

# Switch to ds4 (stop whichever vLLM is up first)
docker stop vllm-qwen35    # or qwen80b-vllm
sudo systemctl start ds4-ssd

# Fallback: 80B
sudo systemctl stop ds4-ssd; docker stop vllm-qwen35 2>/dev/null; docker start qwen80b-vllm
```

## Stopping on failures

If something doesn't work, stop and ask. Do not silently work around failures,
retry indefinitely, or use `--no-verify`/`--force` flags.
