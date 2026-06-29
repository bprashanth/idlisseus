# Setup

Base system setup for this DGX Spark, and the core stack (Odysseus + ds4) that everything else
in this repo builds on. For switching/adding *models*, see [models.md](models.md). For the chat
UI specifically, see [odysseus.md](odysseus.md).

## Hardware and OS facts that shape everything else here

- **Unified memory.** This is a DGX Spark (Grace CPU + GB10 Blackwell GPU): CPU and GPU share
  the same 121GB of RAM (`free -h`, not `nvidia-smi`, is the reliable way to see how much a
  loaded model is actually using — `nvidia-smi` reports memory as "Not Supported" on this
  device). A model that's "loaded" is using regular system RAM, not a separate VRAM pool. This
  is why only one large model can be resident at a time — see [models.md](models.md).
- Docker + NVIDIA Container Toolkit + passwordless sudo were already present/working when this
  setup began (`docker run --gpus all ...` works out of the box).
- Tailscale is the access path for this box; nothing here is exposed on the public internet or
  even the bare LAN — see "Security posture" below.

## Base packages (one-time)

```bash
sudo apt update
sudo apt install -y git curl wget build-essential cmake pkg-config \
  python3 python3-venv python3-pip nodejs npm nginx jq htop nvtop unzip
```

Docker and the NVIDIA Container Toolkit follow their standard install docs for the host OS; both
were already functional on this box.

## Repo layout

```text
idlisseus/
  README.md              quickstart — start here
  docs/                   you are here
  deploy/                 systemd units + docker run scripts for every model, Hermes config tools
  ds4/                    DwarfStar (ds4) source + built binaries (binaries gitignored)
  models/                 downloaded GGUF weights for ds4 (gitignored, ~81GB)
  ds4-kv/                 ds4's on-disk KV cache (gitignored)
  odysseus/               Odysseus source + .env (gitignored) + docker-compose.yml
  benchmark/              Benchmark 1: ds4-agent vs Cursor agent
  benchmark2_hermes/      Benchmark 2: Hermes Agent vs raw ds4-agent; ds4 vs Nemotron-3-Super
  benchmark3_seed_oss/    Benchmark 3: Seed-OSS-36B vs ds4, literature/document synthesis
  PLAN.md                 original build plan for the base POC, with revision notes
```

Each `benchmark*/` directory has its own `PLAN.md` (and most have a `CHECKPOINT.md` — an
append-only log of what happened, in what order, written so a fresh agent picking this up after
a context reset can read it and know exactly where things stand without re-deriving anything).

## What runs natively vs. in Docker

| Component | How it runs | Why |
|---|---|---|
| `ds4-server` | **Native systemd service** (`deploy/ds4.service`) | ds4 is a hand-written C/CUDA binary, not a container image — no reason to add Docker overhead |
| Other model servers (Nemotron-3, Seed-OSS, ...) | **Docker** (`vllm/vllm-openai` image) | vLLM ships as a container image; this is also how NVIDIA's own deployment guides expect it to run |
| Odysseus | **Docker Compose** (`odysseus/docker-compose.yml`) | ships as a multi-container app (app + ChromaDB + SearXNG + ntfy) |
| Hermes Agent | **Docker** (`nousresearch/hermes-agent` image), CLI mode only | ships as a container image; gateway mode (messaging bridge) is explicitly unused here |

## Starting Odysseus (the chat UI)

```bash
cd odysseus
docker compose up -d                  # containers auto-restart on reboot (unless-stopped)
docker compose logs -f odysseus       # admin password is printed here on first boot
```

Open `http://localhost:7000` (or via the Tailscale tunnel — see below) and log in as `admin`.
Day-to-day Odysseus operation (adding users, registering model endpoints, the Pro/Flash alias
gotcha) is in [odysseus.md](odysseus.md).

## Remote access from a laptop (SSH + Tailscale)

This host's Tailscale IP is reachable directly, but Odysseus binds to `127.0.0.1` only (and the
benchmark result files are just files on disk) — so use an SSH tunnel:

```bash
ssh -L 7000:127.0.0.1:7000 -L 8001:127.0.0.1:8001 beeps@<this-host-tailscale-IP>
```

Then on your laptop: `http://localhost:7000` for Odysseus, `http://localhost:8001/` for a
plain static file server (run `python3 -m http.server 8001` from the repo root on this host) to
browse benchmark dashboards/reports/transcripts directly.

## Security posture (apply this to any new model/service)

- Every model server binds to the **Docker bridge IP** (`172.17.0.1` on this box, check with
  `ip -4 addr show docker0`), not `0.0.0.0` and not `127.0.0.1`. This makes it reachable from
  other Docker containers (Odysseus, Hermes) via `host.docker.internal`, but **not** reachable
  from the LAN/Tailscale interface — this host's firewall is otherwise open (`ufw` inactive), so
  this is the only thing standing between a raw, unauthenticated model API and the network.
- If `docker0`'s subnet ever changes, every `--host`/`-p` flag referencing `172.17.0.1` across
  `deploy/` needs updating to match.
- No cloud API keys are configured anywhere on this box (checked explicitly when setting up
  Hermes — see [agents.md](agents.md)) — there is no path for any local tool to silently reach
  a paid cloud backend instead of the local model you intended.

## Known issues carried over from the base POC build

- **`apt-get` OOM bug during the Odysseus image build.** On first attempt, `apt-get install`
  inside Odysseus's Dockerfile grew to ~123GB of anonymous memory and was OOM-killed (confirmed
  via `dmesg`). Didn't reproduce on a clean retry with the full 121GB free and no concurrent
  downloads. If it recurs, split that Dockerfile's single big `RUN apt-get install -y <12
  packages>` line into 2-3 smaller `RUN` steps.
- **Large downloads on this network sometimes stall on individual file chunks**, not just slow
  down — confirmed twice (once for Nemotron-3's weights, see `benchmark2_hermes/CHECKPOINT.md`).
  Symptom: a download directory's total size stops growing for 10+ minutes while the process is
  still "running." Fix: stop and restart the download/container; `huggingface_hub` resumes only
  the stuck shard(s), not the whole thing. See [models.md](models.md) for per-model notes.
