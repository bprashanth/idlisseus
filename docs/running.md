# Running the stack

Operational detail for the box: what to start, what is listening where, and how
to check it is alive. Moved here out of the README so the README can stay about
the product.

The machine is a DGX Spark GB10 with 121 GB of unified memory. CPU and GPU share
that pool, so `free -h` is the honest view of what a loaded model is using.
`nvidia-smi` reports memory as "Not Supported" on this device.

## Start

```bash
docker start vllm-qwen35                          # Qwen3.5-122B (primary), port 8001
cd chatbots/odysseus && docker compose up -d      # the UI, https://chat.idli.cc
```

After changing anything under `chatbots/odysseus/static/`, rebuild. Static files
are baked into the image, so a plain restart will serve the old ones.

```bash
cd chatbots/odysseus
docker compose build odysseus && docker compose up -d --force-recreate odysseus
```

## Models

| Model | State | RAM | Speed |
|-------|-------|-----|-------|
| Qwen3.5-122B-A10B INT4+FP8 | active, primary (`vllm-qwen35`, port 8001) | ~128 Gi @256K | ~52 tok/s |
| Qwen3-Next-80B FP8 | fallback (`qwen80b-vllm`, port 8001) | 110 Gi | 3-20s/turn |
| DeepSeek V4 Flash (ds4) | stopped (`ds4-ssd.service`, port 8000) | 121 Gi (SSD) | 60-190s/turn |
| Seed-OSS-36B AWQ | stopped | ~42 Gi | ~30s/turn |
| Qwen3.5-2B (sidekick) | stopped | ~10 Gi | 4-5s/turn |

122B, 80B and ds4 each need the whole memory pool, so exactly one runs at a time.
Switching means stopping the current one first.

```bash
docker stop vllm-qwen35 && sudo systemctl start ds4-ssd     # to ds4
sudo systemctl stop ds4-ssd && docker start vllm-qwen35     # back to 122B
```

Per-model configs, run scripts and systemd units live in [`models/`](../models/),
with more detail in [`models/index.md`](../models/index.md).

## Site packs

A site pack is served by its own bridge process, one per place. The chat UI talks
to it through a server-side proxy, so bridge tokens never reach the browser. Packs
bind to the Docker bridge address only.

Valparai runs on port 7012 (ecology) and 7013 (synthetic livelihoods). Start and
stop procedure is in [`dss/SITE_PACK_DEPLOYMENT.md`](../dss/SITE_PACK_DEPLOYMENT.md).

## Network

```
Browser (anywhere, no VPN)
  -> https://chat.idli.cc          Cloudflare Access, email OTP gate
    -> Cloudflare Tunnel           cloudflared systemd service on the Spark
      -> localhost:7000            the UI, Docker Compose
        -> 172.17.0.1:8001         the model, vLLM
```

Model and bridge ports bind to `172.17.0.1`, the Docker bridge. Nothing model
shaped is reachable from the internet. Cloudflare Access is the only door, and
opening another port to get around it defeats the whole arrangement.

Adding a teammate is one page: [`docs/access.md`](access.md).

## Health checks

```bash
curl -s http://172.17.0.1:8001/v1/models     # the model
curl -s http://172.17.0.1:7012/health        # a site pack bridge
sudo systemctl status cloudflared            # the tunnel
docker ps                                    # everything else
```

One failure mode worth knowing: the bridge `/health` reports on the host process,
not on the container it execs into. If chats hang at "Selecting skills" while
health says ok, check that `hermes-live` is actually up. It has no restart policy,
so a reboot leaves it down.

```bash
docker ps -a --format '{{.Names}}\t{{.Status}}' | grep hermes
docker start hermes-live
```

## Tests

```bash
cd chatbots/odysseus && ./venv/bin/python -m pytest tests/ -q
```
