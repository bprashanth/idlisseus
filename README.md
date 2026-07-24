# Idlisseus — AI Assistant for NGO Teams

Self-hosted LLM stack on a DGX Spark GB10. Chatbot + agentic data science workflows,
accessible to the whole team at **https://chat.idli.cc** — no VPN, no install.

## Quickstart

```bash
docker start vllm-qwen35                          # Qwen3.5-122B (primary), port 8001
cd chatbots/odysseus && docker compose up -d      # Idlisseus UI → https://chat.idli.cc
```

**Active model:** **Qwen3.5-122B-A10B INT4+FP8** (`vllm-qwen35`) on port 8001 (~52 tok/s).
The albond GB10 build — see [`models/qwen3.5-122b/`](models/qwen3.5-122b/). 80B is now the fallback.
**UI:** Idlisseus — pink/white theme, multi-user, agent mode, document library
**Access:** Cloudflare Tunnel → `chat.idli.cc` (HTTPS, Cloudflare Access email gate)

To invite a team member: see [`docs/access.md`](docs/access.md).

## Architecture

```
Browser (anywhere, no VPN)
  → https://chat.idli.cc  (Cloudflare Access — email OTP gate)
    → Cloudflare Tunnel  (cloudflared systemd service on Spark)
      → localhost:7000  (Idlisseus / Docker Compose)
        → 172.17.0.1:8001  (Qwen3.5-122B-A10B INT4+FP8 / vLLM)
```

Model ports are bound to `172.17.0.1` (Docker bridge only) — never exposed to the internet.

## Repo layout

```
models/         per-model configs, run scripts, systemd services
agents/         agent harnesses (Hermes token proxy)
chatbots/       UI deployments (odysseus/ = Idlisseus)
benchmarks/     benchmark runs (7 rounds ds4→80B→122B) + semantic_broker (active)
docs/           cross-cutting docs: access, architecture, setup
ds4/            ds4 C+CUDA inference engine source (own git repo — gitignored here)
ds4-kv/         ds4 KV disk cache (runtime, gitignored)
```

Weights, KV cache, venvs, `.env`/creds, and downloaded corpora are **gitignored** —
see [`REPLICATION.md`](REPLICATION.md) for what to download to reproduce this.

## Docs

| Doc | What's in it |
|-----|-------------|
| [`docs/IDLI_INSIGHT_MODEL_COMPOSITION.md`](docs/IDLI_INSIGHT_MODEL_COMPOSITION.md) | **Start here for Idli Insight** — live Codex CLI + 9B composition, request path, model responsibilities, isolation, and invariants |
| [`docs/VISUAL_FIRST_AOI_DATA_DESIGN.md`](docs/VISUAL_FIRST_AOI_DATA_DESIGN.md) | **Future design** — acquisition, indexing, visual-ready data products, model surfaces, governance, and acceptance tests |
| [`dss/GENERIC_VISUAL_CHATBOT_HANDOFF.md`](dss/GENERIC_VISUAL_CHATBOT_HANDOFF.md) | **Generic visual-chat handoff** — current/future boundary, ownership, reading order, shared contracts, and parallel work |
| [`dss/SITE_PACK_DEPLOYMENT.md`](dss/SITE_PACK_DEPLOYMENT.md) | **Cross-benchmark site deployment** — pack/launcher contracts and start, stop, restart, isolation, and validation |
| [`docs/access.md`](docs/access.md) | **Team access** — invite users, network flow, cloudflared |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture, model inventory, next steps |
| [`models/index.md`](models/index.md) | All models — specs, memory, start/stop |
| [`agents/index.md`](agents/index.md) | Agent harnesses, tool list, security model |
| [`chatbots/index.md`](chatbots/index.md) | Idlisseus features, citation, data science workflow |
| [`benchmarks/index.md`](benchmarks/index.md) | Benchmark results, hypotheses, key takeaways |
| [`REPLICATION.md`](REPLICATION.md) | **What to download** to reproduce from a fresh clone (weights, image, EE auth, corpus) |

## Model inventory

| Model | State | RAM | Speed |
|-------|-------|-----|-------|
| Qwen3.5-122B-A10B INT4+FP8 | **active / primary** (`vllm-qwen35`, port 8001) | ~128 Gi @256K | ~52 tok/s |
| Qwen3-Next-80B FP8 | fallback (`qwen80b-vllm`, port 8001) | 110 Gi | 3–20s/turn |
| DeepSeek V4 Flash (ds4) | stopped (`ds4-ssd.service`, port 8000) | 121 Gi (SSD) | 60–190s/turn |
| Seed-OSS-36B AWQ | stopped | ~42 Gi | ~30s/turn |
| Qwen3.5-2B (sidekick) | stopped | ~10 Gi | 4–5s/turn |

122B / 80B / ds4 each need the full unified-memory pool — only one runs at a time.
Switch to ds4: `docker stop vllm-qwen35 && sudo systemctl start ds4-ssd`. Full details in [`models/index.md`](models/index.md).

## Check system health

```bash
curl -s http://172.17.0.1:8001/v1/models    # 80B
curl -s http://172.17.0.1:8000/v1/models    # ds4 (if switched)
sudo systemctl status cloudflared            # tunnel
docker ps                                    # running containers
```
