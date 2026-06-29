# Model Inventory

All model weights on this machine as of 2026-06-26. Keep this updated before purging.

## Active / in use

| Model | Path | Size | Format | Notes |
|-------|------|------|--------|-------|
| DeepSeek V4 Flash (Q2) | `models/deepseek-v4-flash/*.gguf` | 81 GB | GGUF IQ2XXS | Served by ds4-server (DwarfStar). Primary model. |
| Seed-OSS-36B-Instruct (BF16) | `~/.cache/huggingface/hub/models--ByteDance-Seed--Seed-OSS-36B-Instruct` | 68 GB | safetensors BF16 | Served by vLLM. **Cannot coexist with ds4 full RAM (108 GB + 72 GB > 121 GB).** |
| Seed-OSS-36B-Instruct-AWQ (INT4) | `~/models/Seed-OSS-36B-AWQ` | 21 GB | safetensors AWQ | Served by vLLM. Coexists with ds4 SSD streaming (~83 + ~34 = 117 GB). |

## Candidates for purging

| Model | Path | Size | Why it might be purged |
|-------|------|------|------------------------|
| Nemotron-3-Super-120B NVFP4 | `~/.cache/huggingface/hub/models--nvidia--NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4` | 75 GB | B2/B4 benchmarks complete. Too slow for agentic tasks (4-5 tok/s). No planned further use. |
| Qwen3-Next-80B-FP8 (local copy) | `~/models/Qwen3-Next-80B-FP8/` | 77 GB | B4 complete. Poor agentic behavior (curl-google loop). Not competitive with ds4 for tool use. Keep if planning further Qwen experiments. |
| Qwen3-Next-80B-FP8 (HF cache) | `~/.cache/huggingface/hub/models--Qwen--Qwen3-Next-80B-A3B-Instruct-FP8` | 4.6 GB | Partial HF cache blob — the real weights are in ~/models/, this is just metadata/pointers. |
| Qwen3.5-2B (HF cache) | `~/.cache/huggingface/hub/models--Qwen--Qwen3.5-2B` | 4.3 GB | B4 Stage 2 sidekick. Too small for real use (hallucinations, garbled translation). |
| Qwen3.5-2B (local copy) | `~/models/qwen3.5-2b/` | 64 MB | Same as above; tiny. |
| Seed-OSS-36B BF16 (HF cache) | `~/.cache/huggingface/hub/models--ByteDance-Seed--Seed-OSS-36B-Instruct` | 68 GB | Once AWQ version is validated, the BF16 version is redundant (AWQ coexists with ds4; BF16 doesn't). Purge after confirming AWQ quality is acceptable. |

## Docker images

| Image | Size | Keep? |
|-------|------|-------|
| `hermes-agent-local:latest` | 3.76 GB | YES — custom benchmark image |
| `nousresearch/hermes-agent:latest` | 3.75 GB | Can purge once hermes-agent-local is stable (it's the base) |
| `vllm/vllm-openai:cu130-nightly` | 23.3 GB | YES — used to serve Seed-OSS |

## Quick purge commands (run when ready)

```bash
# Nemotron (75 GB)
rm -rf ~/.cache/huggingface/hub/models--nvidia--NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4

# Qwen3-Next local copy (77 GB) — confirm not needed first
rm -rf ~/models/Qwen3-Next-80B-FP8/

# Qwen3.5-2B (4.3 GB + 64 MB)
rm -rf ~/.cache/huggingface/hub/models--Qwen--Qwen3.5-2B ~/models/qwen3.5-2b/

# Qwen3-Next HF metadata (4.6 GB)
rm -rf ~/.cache/huggingface/hub/models--Qwen--Qwen3-Next-80B-A3B-Instruct-FP8

# Seed-OSS BF16 (68 GB) — only after AWQ validated
rm -rf ~/.cache/huggingface/hub/models--ByteDance-Seed--Seed-OSS-36B-Instruct

# Upstream Hermes image (3.75 GB) — only after hermes-agent-local confirmed stable
docker rmi nousresearch/hermes-agent:latest
```
