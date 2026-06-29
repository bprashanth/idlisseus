# Idlisseus — AI Assistant for NGO Teams

Self-hosted LLM stack on a DGX Spark GB10. Chatbot + agentic data science workflows,
accessible to the whole team at **https://chat.idli.cc** — no VPN, no install.

## Quickstart

```bash
docker start qwen80b-vllm                        # 80B model (~9 min cold load)
cd chatbots/odysseus && docker compose up -d     # Idlisseus UI → https://chat.idli.cc
```

**Active model:** Qwen3-Next-80B FP8 on port 8001 (~3-20s/response)
**UI:** Idlisseus — pink/white theme, multi-user, agent mode, document library
**Access:** Cloudflare Tunnel → `chat.idli.cc` (HTTPS, Cloudflare Access email gate)

To invite a team member: see [`docs/access.md`](docs/access.md).

## Architecture

```
Browser (anywhere, no VPN)
  → https://chat.idli.cc  (Cloudflare Access — email OTP gate)
    → Cloudflare Tunnel  (cloudflared systemd service on Spark)
      → localhost:7000  (Idlisseus / Docker Compose)
        → 172.17.0.1:8001  (Qwen3-Next-80B FP8 / vLLM)
```

Model ports are bound to `172.17.0.1` (Docker bridge only) — never exposed to the internet.

## Repo layout

```
models/         per-model configs, run scripts, systemd services
agents/         agent harnesses (Hermes token proxy)
chatbots/       UI deployments (odysseus/ = Idlisseus)
benchmarks/     benchmark runs (6 rounds, ds4 through 80B)
docs/           cross-cutting docs: access, architecture, setup
ds4/            ds4 C+CUDA inference engine source (own git repo)
ds4-kv/         ds4 KV disk cache (runtime)
```

## Docs

| Doc | What's in it |
|-----|-------------|
| [`docs/access.md`](docs/access.md) | **Team access** — invite users, network flow, cloudflared |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture, model inventory, next steps |
| [`models/index.md`](models/index.md) | All models — specs, memory, start/stop |
| [`agents/index.md`](agents/index.md) | Agent harnesses, tool list, security model |
| [`chatbots/index.md`](chatbots/index.md) | Idlisseus features, citation, data science workflow |
| [`benchmarks/index.md`](benchmarks/index.md) | Benchmark results, hypotheses, key takeaways |

## Model inventory

| Model | State | RAM | Speed |
|-------|-------|-----|-------|
| Qwen3-Next-80B FP8 | **active** (`qwen80b-vllm`, port 8001) | 110 Gi | 3–20s/turn |
| DeepSeek V4 Flash (ds4) | stopped (`ds4-ssd.service`, port 8000) | 121 Gi (SSD) | 60–190s/turn |
| Seed-OSS-36B AWQ | stopped | ~42 Gi | ~30s/turn |
| Qwen3.5-2B (sidekick) | stopped | ~10 Gi | 4–5s/turn |

ds4 and 80B cannot coexist. Switch: `docker stop qwen80b-vllm && sudo systemctl start ds4-ssd`

## Check system health

```bash
curl -s http://172.17.0.1:8001/v1/models    # 80B
curl -s http://172.17.0.1:8000/v1/models    # ds4 (if switched)
sudo systemctl status cloudflared            # tunnel
docker ps                                    # running containers
```
