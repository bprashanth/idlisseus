# Replication — what to download from a fresh clone

This repo holds **code, configs, docs, and benchmark write-ups** — not weights,
credentials, or downloaded corpora (all gitignored). Here's everything you'd need
to fetch to reproduce the results, roughly in order.

## 0. Hardware / platform

Everything here targets a **DGX Spark GB10** (arm64, GB10 GPU, **121.6 GiB unified
memory**, SM121, 273 GB/s LPDDR5x). SM121 has no datacenter FP4 and needs vLLM
compiled from source. Other machines will need different quantization/backends.

## 1. Models (gitignored — download to `~/models/`)

Use **host-level** downloads with `hfd.sh` + `HF_ENDPOINT=https://hf-mirror.com`
+ `aria2c -x 8 -j 2` (resumable; the HF CDN throttles hard, the mirror sustains
10–32 MB/s). Never download inside a serving container; mount the finished dir
read-only. (See the download-strategy notes below.)

- **Qwen3.5-122B-A10B INT4+FP8 — PRIMARY (~71 GB).** The albond GB10 build:
  <https://github.com/albond/DGX_Spark_Qwen3.5-122B-A10B-AR-INT4>
  ```bash
  HF_ENDPOINT=https://hf-mirror.com bash /tmp/hfd.sh \
    Intel/Qwen3.5-122B-A10B-int4-AutoRound \
    --tool aria2c -x 8 -j 2 --local-dir ~/models/qwen35-122b-hybrid-int4fp8
  ```
  Then build vLLM 0.19.1 from source for SM121 and serve per
  [`models/qwen3.5-122b/README.md`](models/qwen3.5-122b/README.md) →
  container `vllm-qwen35` on `172.17.0.1:8001`, served name `qwen`.
- **Qwen3-Next-80B FP8 — fallback (~77 GB).** `~/models/Qwen3-Next-80B-FP8/`; serve
  with `--moe-backend marlin` (see [`models/qwen3-next-80b/`](models/qwen3-next-80b/)).
- **ds4 / DeepSeek-V4-Flash — optional (670B, ~82 GB GGUF).** The `ds4/` engine is
  its **own git repo** (gitignored here) — clone it separately; download the GGUF
  into `models/deepseek-v4-flash/`. Only needed to reproduce B1–B6.
- Seed-OSS-36B / Qwen3.5-2B — optional, only for their benchmarks.

## 2. Hermes agent (for the semantic_broker experiments)

```bash
docker pull nousresearch/hermes-agent:latest
bash agents/hermes/build.sh          # -> hermes-agent-local
```
`build.sh` layers on jq/wget/sudo **and preinstalls `earthengine-api` + `pymupdf`**
and sets `ENV HOME=/opt/data` (both required — see
[`benchmarks/semantic_broker/CONNECTORS.md`](benchmarks/semantic_broker/CONNECTORS.md)).
Point Hermes at the model (once): its `~/.hermes/config.yaml` `model.default` →
`qwen` @ `http://172.17.0.1:8001/v1`.

## 3. Earth Engine auth (for the connectors)

```bash
earthengine authenticate           # creates ~/.config/earthengine/credentials
# stage into the Hermes sandbox HOME (uid 10000), NOT ~/.hermes/.config:
sudo mkdir -p ~/.hermes/home/.config/earthengine
sudo cp ~/.config/earthengine/credentials ~/.hermes/home/.config/earthengine/credentials
sudo chown -R 10000:10000 ~/.hermes/home
sudo chown -R 10000:10000 ~/.hermes            # so the agent (uid 10000) can cd into /opt/data
```
Set your own GEE project (we use `plantwars`) — edit the `project=` in the connectors
or the creds file. GBIF needs no key.

## 4. semantic_broker corpus (gitignored `assets/`)

Regenerate the S. India conservation corpus (NCF Zenodo community + specific
records + a few distractor papers):
```bash
cd benchmarks/semantic_broker
# NCF Zenodo community bulk (text/data files, media & >40MB skipped):
python3 <the downloader in git history: scratchpad/dl_ncf.py> assets/ncf_zenodo
# plus the gold/distractor records listed in DATASETS.md (Zenodo 10426971, 10630501,
# 13340613, GBIF Manar/Anamalai, Prasad 2018 + Osuri 2024 PDFs).
```
Exact sources + DOIs are in [`DATASETS.md`](benchmarks/semantic_broker/DATASETS.md).
The pre-staged query inputs (`queries/data/*.csv`) **are** committed, so the
connector runs (`run_connectors.sh`) work without re-downloading the corpus.

## 5. Idlisseus / Odysseus UI (optional — the chatbot)

```bash
cd chatbots/odysseus
cp .env.example .env         # then set SECURE_COOKIES=true etc. (.env is gitignored)
docker compose up -d
```

## 6. Reproduce the headline connector result

With 122B up + Hermes built + EE staged:
```bash
cd benchmarks/semantic_broker
bash run_connectors.sh "Which restoration sites are most exposed to wildfire risk? Rank them." \
     /opt/data/query_data/restoration_sites.csv
```
Expect a correct fire ranking (Akkamalai top) in ~2 min — vs the raw v-1 run that
never completed. See [`CONNECTORS_DESIGN.md`](benchmarks/semantic_broker/CONNECTORS_DESIGN.md) §Validation.

## What is NOT in git (fetch/generate yourself)

`~/models/*` weights · `ds4/` source repo · `ds4-kv/` · `chatbots/odysseus/.env`
& `data/` · EE credentials · `benchmarks/semantic_broker/assets/` (corpus) &
`runs/` (logs) · all venvs · Docker images.

## Download-strategy notes (flaky-network survival)

- `hfd.sh` at `/tmp/hfd.sh` (re-fetch: `curl -O https://hf-mirror.com/hfd/hfd.sh`).
- `HF_ENDPOINT=https://hf-mirror.com` + `aria2c -x 8 -j 2`; resumes on re-run.
- 403s on byte-range boundaries in the aria2c log are normal (signed-CDN range
  limits; aria2c retries internally).
- Always download at host level, then mount `-v ~/models/<name>:/model:ro`.
