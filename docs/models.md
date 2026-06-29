# Models

Three models have been brought up on this box so far: **ds4 / DeepSeek V4 Flash** (native, the
default/checkpoint state), **Nemotron-3-Super-120B** (vLLM/Docker), and **Seed-OSS-36B-Instruct**
(vLLM/Docker). **Only one large model can be resident at a time** — see "Why you can't run two
at once" below — so "switching models" always means: stop whichever is running, start the other.

**Current checkpoint state: ds4 is the only model running.** Odysseus and Hermes are both
pointed at it. This is intentional — see the bottom of this page.

## Why you can't run two at once

Unified memory: ds4 alone uses ~108GB of the 121GB total (`free -h` while it's running). That
leaves ~13GB free — not enough for any of the other models, even at aggressive quantization
(36B-class models need ~16-20GB minimum at 3-4 bit; the ones tried here are unquantized/lightly
quantized and need 70-80GB). If you want true concurrent serving of two models, the fix is more
RAM or a much smaller second model — not something to improvise per-session.

## ds4 / DeepSeek V4 Flash (the default)

- **Runs as:** native systemd service, not a container (ds4 is a hand-written C/CUDA binary).
- **Unit file:** `deploy/ds4.service` (installed at `/etc/systemd/system/ds4.service`).
- **Weights:** `models/deepseek-v4-flash/*.gguf` (q2-imatrix quant, ~81GB, symlinked as
  `ds4/ds4flash.gguf`), gitignored.
- **Bind address:** `172.17.0.1:8000` (Docker bridge IP — see `setup.md` "Security posture").
- **Aside, worth knowing:** Odysseus's model picker shows both `deepseek-v4-flash` and
  `deepseek-v4-pro` as options. **These are the same loaded weights** — ds4 serves the one GGUF
  you downloaded under two aliases (confirmed via `/v1/models`, where the `deepseek-v4-pro`
  entry's own `"name"` field says `"DeepSeek V4 Flash"`; also stated directly in
  `ds4-server --help`: *"Model endpoint aliases include deepseek-v4-flash and deepseek-v4-pro;
  both serve the loaded GGUF."*). Querying each alias even produces different (and both
  incorrect) self-reported parameter counts — pick either, there's no real second model.

```bash
sudo systemctl start ds4      # loads the 81GB GGUF, ~20-30s
sudo systemctl stop ds4       # frees ~108GB — do this before starting any other model
sudo systemctl status ds4
sudo journalctl -u ds4 -f     # logs
```

Verify it's up:
```bash
curl -s http://172.17.0.1:8000/v1/models
curl -s http://172.17.0.1:8000/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"hi"}],"stream":false}'
```

**Measured characteristics:** ~15 tokens/sec single-stream decode, **no request batching**
(concurrent requests fully serialize — confirmed with a 5-way concurrency test, see
`README.md`/Benchmark 1). 100K context (`--ctx 100000`).

**SSD streaming mode (do not use for production):**
ds4 supports `--ssd-streaming --ssd-streaming-cache-experts <N>GB` to stream expert weights
from NVMe rather than mmap'ing the full model into RAM. Tested at 20GB and 60GB cache sizes:
- Startup: nearly instant (~1 sec vs ~2 min) — only 0.99GB token embedding loaded at start
- RAM after warmup: 80-83GB (not a persistent saving — experts fill the cache after a few queries)
- Speed: 3-9 tok/s vs 15 tok/s baseline (2-5x slower, highly variable per query type)
- Verdict: not suitable for production. The RAM saving after warmup is only ~25GB and the speed
  cost is severe. Use normal mode (`sudo systemctl start ds4`) for all production/benchmark work.

## Nemotron-3-Super-120B-A12B (NVFP4, via vLLM)

- **Runs as:** Docker container (`vllm/vllm-openai:cu130-nightly`), not a systemd service.
- **Start script:** `deploy/nemotron-3-super/run.sh` (also needs
  `deploy/nemotron-3-super/super_v3_reasoning_parser.py`, fetched from the model repo, already
  saved here).
- **Weights:** downloaded on first run to `~/.cache/huggingface` (~76GB, not gitignored from
  this repo because it's outside the repo entirely — `~/.cache/huggingface` is shared across all
  HF-downloaded models on this box).
- **Source guide:** NVIDIA's own DGX Spark deployment guide —
  https://github.com/NVIDIA-NeMo/nemotron/tree/main/usage-cookbook/Nemotron-3-Super/SparkDeploymentGuide

```bash
sudo systemctl stop ds4                       # free the memory first
bash deploy/nemotron-3-super/run.sh
# first run: downloads ~76GB, takes 1-2+ hours on this network — see script comments for the
# known download-stall issue and how to recover from it
curl -s http://172.17.0.1:8000/v1/models      # ready when this responds
```

To switch back:
```bash
docker stop nemotron-vllm                     # has --rm, this also removes the container
sudo systemctl start ds4
```

**Known idiosyncrasies (see `deploy/nemotron-3-super/run.sh` comments and
`benchmark2_hermes/REPORT.md` for full detail):**
- `--max-model-len 1000000` exceeds the model's real trained context (262,144) — vLLM allows it
  via `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` per NVIDIA's example, but warns positions beyond 262,144
  can produce NaN/CUDA errors. Never triggered in our testing, but don't assume it's safe at
  genuinely long contexts without checking.
- Self-identifies as "ChatGPT, trained by NVIDIA" when asked what model it is — a training-data
  contamination artifact, not a serving bug.
- **This exact config (NVFP4 + MTP speculative decoding) suffers severe throughput collapse
  under long, accumulating agentic conversations** — confirmed via vLLM's own metrics (MTP
  acceptance rate collapsing at longer context) and 96% sustained GPU utilization (genuinely
  computing, not hung). It ran for 1h52m and hit Hermes's 60-turn budget without finishing a
  research task that ds4 finished in 25 minutes. If retrying for agentic work, try dropping
  `--speculative_config` first.

## Seed-OSS-36B-Instruct (BF16, via vLLM)

- **Runs as:** Docker container, same image as Nemotron.
- **Start script:** `deploy/seed-oss-36b/run.sh`.
- **Weights:** downloaded on first run to `~/.cache/huggingface` (~72GB BF16, not gated).
- **Source guide:** https://docs.vllm.ai/projects/recipes/en/latest/Seed/Seed-OSS-36B.html
  (NVIDIA's example there uses `--tensor-parallel-size 8` for a multi-GPU node — adapted to `1`
  for this single-GPU box).

```bash
sudo systemctl stop ds4
bash deploy/seed-oss-36b/run.sh
# first run: downloads ~72GB, ~1.5 hours on this network
curl -s http://172.17.0.1:8000/v1/models
```

To switch back:
```bash
docker stop seed-oss-vllm
sudo systemctl start ds4
```

**Known idiosyncrasies (see `benchmark3_seed_oss/CHECKPOINT.md` for full detail):**
- Embeds chain-of-thought reasoning inline in the response content as
  `<seed:think>...</seed:think>` (not a separate `reasoning` field like Nemotron's parser) —
  strip this if you want just the final answer.
- **Defaults to extensive reasoning even for trivial prompts**, and decodes at ~3 tokens/sec on
  this hardware with this config (vs. ds4's ~15 tok/s) — measured 13-20x slower than ds4 on
  short interactive queries, and 2.6-6.4x slower on long document-synthesis tasks. This was the
  opposite of the hypothesis that motivated testing it ("maybe better for quick answers"). The
  model card mentions a "Thinking Budget" feature that may be tunable to reduce this — **not yet
  tried**; don't write the model off for interactive use until that's been tested.
- No speculative decoding configured (unlike Nemotron) — doesn't suffer the same long-context
  collapse failure mode.

## Pointing Odysseus and Hermes at whichever model is running

- **Odysseus:** model endpoints are registered in its database via the admin UI (Settings ->
  Models) or the `/api/model-endpoints` API — see [odysseus.md](odysseus.md). Only `ds4` is
  currently registered there; Nemotron-3 and Seed-OSS were only ever tested directly via API/
  Hermes, never wired into Odysseus.
- **Hermes:** `deploy/hermes/point_at_model.py <model-name> <base-url>` — see
  [agents.md](agents.md) for why this needs a dedicated script rather than a one-line edit.

## Trying a new model (e.g. Qwen) — minimal checklist

1. Check it fits: `df -h /` (disk) and do the unified-memory math against ds4's ~108GB baseline
   (see "Why you can't run two at once" above).
2. Check it's not gated on Hugging Face (`curl -s "https://huggingface.co/api/models/<repo>"`,
   look at `"gated"`) — if gated, you need an `HF_TOKEN` and a human to accept the license first.
3. If it ships an official vLLM serving guide, start from that, adapted to
   `--tensor-parallel-size 1` (single GPU) and bound to `172.17.0.1:8000`, not `0.0.0.0`.
4. Copy `deploy/seed-oss-36b/run.sh` as a template — it's the simplest of the two vLLM examples
   here (no speculative decoding, no quantization flags to adapt).
5. Smoke test the bare server first (non-streaming + streaming `/v1/chat/completions`) *before*
   touching Hermes or Odysseus.
6. Watch for the download-stall issue (`setup.md`) on first weights download.
7. See `benchmark2_hermes/PLAN_MODEL.md` for the full phased procedure this checklist is
   condensed from (download → smoke test → Hermes tool-calling test), including the GO/NO-GO
   gate philosophy: stop and report on a real failure rather than silently working around it.

## Downloading large model weights on this box — practical guide

**Do not use** `docker run vllm/... --model <X>` or `hf download` / `huggingface-cli download`
for weights >2GB. Both hf_transfer and the `hf` CLI v1.21.0 open 28+ parallel connections and
buffer all data in Python process memory before writing to disk. When HF's CDN throttles the
connections (which it does on this network), the download hangs with data in memory and 0 bytes
on disk. Restarting discards everything buffered.

**The right approach: `wget -c` directly on the raw file URL, into the blob cache.**
```bash
# Stop ds4 first (frees 93GB — download has no memory pressure):
sudo systemctl stop ds4
# Fix HF cache permissions if needed (Docker ran as root):
sudo chown -R beeps:beeps ~/.cache/huggingface/
# Download to the blob directly:
wget -c "https://huggingface.co/<repo>/resolve/main/<filename>" \
     -O "$HOME/.cache/huggingface/hub/models--<Owner>--<Name>/blobs/<sha256>" \
     --progress=dot:giga
# After wget: create snapshot symlinks (skips blobs already present):
HF_HUB_ENABLE_HF_TRANSFER=0 hf download <Owner>/<Name>
```
See `deploy/qwen3.5-2b/wget_download.sh` and `deploy/qwen3-next-80b/wget_download.sh` for
worked examples with the correct blob hashes.

**CDN throttle behavior (confirmed on this network):**
- HF CDN gives an initial burst of ~8-10 MB/s for the first ~1.7-2GB, then throttles to ~70-80 KB/s
- Throttle is IP-based: a fresh connection immediately after throttle is still at ~70 KB/s
- Throttle resets after ~40-45 minutes of inactivity — then the burst is available again
- ModelScope CDN has the same ~70-80 KB/s sustained rate with no burst allowance (slower overall)
- Strategy for >2GB files: download in sessions. After the burst exhausts (~38-40% done for a
  4.6GB file), wait 40-45 min, then restart wget -c. Each restart gets another ~1.7GB burst.
- For files >10GB, budget for multiple throttle+wait cycles (e.g., 8×10.7GB shards × 2 cycles = 16
  restarts) and run downloads unattended overnight if possible.
