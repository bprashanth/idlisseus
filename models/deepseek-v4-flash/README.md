# DeepSeek V4 Flash — ds4

**Model:** DeepSeek-V4-Flash 670B, quantized to IQ2XXS (2-bit mixed, ~200 GB → ~120 GB disk)
**Weights:** `models/deepseek-v4-flash/DeepSeek-V4-Flash-IQ2XXS-*.gguf` (GGUF on internal SSD)
**Inference engine:** ds4 — custom C+CUDA server in `../../ds4/`, built specifically for this model
**Port:** `172.17.0.1:8000` (Docker bridge only)

## Start / stop

```bash
# Start (SSD streaming mode — only mode that fits 121 Gi; normal mode OOMs)
sudo systemctl start ds4-ssd

# Stop
sudo systemctl stop ds4-ssd

# Status / logs
sudo systemctl status ds4-ssd
journalctl -u ds4-ssd -f

# Check serving
curl http://172.17.0.1:8000/v1/models
```

The `ds4.service` file is normal mode (loads all weights into memory) — don't use it on this hardware. Use `ds4-ssd.service` which streams from SSD.

## Key parameters (`ds4-ssd.service`)

```
WorkingDirectory: ../../ds4/
--host 172.17.0.1 --ctx 65536 --ssd-streaming
--kv-disk-dir ../../ds4-kv/  --kv-disk-space-mb 8192
```

## Memory profile

- SSD streaming: 121 Gi active set fits in unified memory
- Cannot coexist with Qwen3-Next-80B (both need full pool)
- Can coexist with Seed-OSS-36B AWQ (~117 Gi combined; tested but unstable)
- Can coexist with Qwen3.5-2B sidekick (~10 Gi extra; stable)

## Speed

Benchmark 6 (3-question chatbot test):
- Average: 121s/turn
- Range: 60–189s depending on context length and SSD streaming hit rate

## API format

OpenAI-compatible `/v1/chat/completions`. Does NOT support Hermes tool-call format natively — use Hermes token proxy (`agents/hermes/`) for tool use.
