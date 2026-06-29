# CLAUDE.md — idlisseus repo

## Repo structure

```
models/          per-model weights, run scripts, systemd services
agents/          agent harness code (hermes/ token proxy)
chatbots/        UI deployments (odysseus/ = Idlisseus)
benchmarks/      benchmark runs (benchmark1_ds4/ through benchmark6_chatbot/)
docs/            cross-cutting docs (access.md, ARCHITECTURE.md, etc.)
ds4/             ds4 C+CUDA source (its own git repo, do not move)
ds4-kv/          ds4 KV disk cache (runtime, do not commit)
```

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
- 80B vLLM binds to `172.17.0.1:8001` (Docker bridge), NOT public
- No cloud API keys on this box — no OpenAI key, no Anthropic key, no HF tokens needed
- Cloudflare Access is the security boundary — do not bypass or open alternative ports
- Never `sudo reboot` unattended; stop containers cleanly first
- `SECURE_COOKIES=true` must stay set in `chatbots/odysseus/.env`

## Model switching

ds4 and 80B cannot coexist (both need full 121 Gi):
```bash
# Switch to 80B
sudo systemctl stop ds4-ssd
docker start qwen80b-vllm

# Switch to ds4
docker stop qwen80b-vllm
sudo systemctl start ds4-ssd
```

## Stopping on failures

If something doesn't work, stop and ask. Do not silently work around failures,
retry indefinitely, or use `--no-verify`/`--force` flags.
