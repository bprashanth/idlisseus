# Hermes Token-Budget Proxy

`deploy/hermes/token_proxy.py` — a thin HTTP proxy that sits between Hermes Agent and vLLM,
correcting the `max_tokens` field in completion requests when the model's tokenizer produces
more tokens per character than Hermes's estimator assumes.

---

## Why this exists

Hermes Agent estimates token counts at roughly **4 characters per token** when computing how
many output tokens to request: `max_tokens = context_window - estimated_prompt_tokens`.

Most models tokenize close enough to this rate that the estimate works.  Qwen3-Next-80B does
not: its BPE tokenizer produces around **2.7 characters per token** — **46% more tokens**
than Hermes predicts.  The result:

```
Hermes estimates prompt:   44 000 tokens  (at 4 chars/tok)
Hermes requests max_tokens: 87 000         (= 131072 - 44000, at 131k context)
Actual prompt tokens:       64 000         (at 2.7 chars/tok)
Actual total:               64000 + 87000 = 151 000  >  131 072  → HTTP 400
```

The overflow is structural: increasing `max_model_len` does not fix it, because Hermes always
requests `max_tokens = context_length - estimated_prompt`, so the overflow is always
`0.46 × estimated_prompt` above the limit, regardless of how large the context window is.

The only correct fix is to cap `max_tokens` so that `actual_prompt + max_tokens ≤ context_length`.

---

## Why a proxy rather than a Hermes config change

There is no `max_output_tokens` or `max_tokens_per_call` setting in Hermes's `config.yaml`
(checked against config schema v30).  The token budget calculation is inside Hermes's inference
loop, not exposed as configuration.

Patching Hermes's source would require maintaining a fork of the container image, which breaks
on every upstream update.  The proxy approach:

- Touches zero Hermes code or config (beyond pointing its `base_url` at the proxy port)
- Works for any future model with the same problem — just add one line to `MODEL_TOKENIZER_RATIOS`
- Transparent passthrough for models not in the table (ds4-flash, Nemotron, etc.)
- Can be stopped independently of both Hermes and vLLM

---

## How it works

```
Hermes ─── POST /v1/chat/completions ──→ proxy :8001
                                              │
                                    Inspect "model" field
                                              │
                          in table?  Yes: divide max_tokens by ratio
                          in table?   No: pass body unchanged
                                              │
                                       Forward to vLLM :8000
                                              │
                           Stream response back to Hermes (chunked)
```

The correction formula: `safe_max_tokens = max(4096, int(max_tokens / ratio))`.

Derivation: if Hermes estimates a prompt of `E` tokens and requests `max_tokens = C - E`,
but the actual prompt is `ratio × E`, then safe output budget = `C - ratio×E`.
Substituting: `C - ratio×E = C - ratio×(C - max_tokens)`.  Dividing by ratio gives a
conservative approximation with ~30% extra headroom beyond the theoretical minimum.

---

## Configuration

Edit `MODEL_TOKENIZER_RATIOS` in `deploy/hermes/token_proxy.py`:

```python
MODEL_TOKENIZER_RATIOS: dict[str, float] = {
    "qwen3-next-80b": 1.46,
    # add other models here as characterised
}
```

The key is the `--served-model-name` value passed to vLLM (which is also what Hermes puts in
the `model` field of its requests).  The value is the measured ratio
`actual_tokens / hermes_estimated_tokens`.  To measure it for a new model:

1. Run a Hermes session long enough to trigger one overflow
2. Look at the vLLM error: `Prompt 65536 tokens + output 87000 tokens = 152536 > 131072`
3. `ratio = actual_prompt / (context_length - requested_max_tokens)`

---

## Deployment

### Install and start the service

```bash
# Install the systemd unit
sudo cp deploy/hermes/hermes-token-proxy.service /etc/systemd/system/
sudo systemctl daemon-reload

# Start (do this before starting Hermes for any benchmark or research session)
sudo systemctl start hermes-token-proxy
sudo journalctl -u hermes-token-proxy -f   # verify it started

# Stop (do this after the Hermes session ends)
sudo systemctl stop hermes-token-proxy
```

The service is intentionally **not enabled** (`WantedBy` is blank in the unit file).  It does
not start on boot.  See `docs/agents.md` for the security rationale.

### Point Hermes at the proxy

```bash
# Route through proxy (use this for all Hermes sessions):
sudo python3 deploy/hermes/point_at_model.py <model-name> http://172.17.0.1:8001/v1

# Examples:
sudo python3 deploy/hermes/point_at_model.py deepseek-v4-flash   http://172.17.0.1:8001/v1
sudo python3 deploy/hermes/point_at_model.py qwen3-next-80b      http://172.17.0.1:8001/v1
```

Note: use `:8001` (proxy) not `:8000` (vLLM direct) when the proxy is running.  The proxy is
a transparent passthrough for `deepseek-v4-flash` — pointing ds4 sessions at the proxy is safe
and avoids having to remember to switch.

### Verify

```bash
# Proxy running?
sudo systemctl status hermes-token-proxy

# Proxy reachable and forwarding to vLLM?
curl -s http://172.17.0.1:8001/v1/models
# → should return the same response as :8000

# Correction firing?  Run a Hermes session and watch the proxy log:
sudo journalctl -u hermes-token-proxy -f
# → [token-proxy] qwen3-next-80b max_tokens: 218000 → 149315  (ratio=1.46)
```

---

## What the proxy does NOT do

- Does not inspect or modify the response from vLLM
- Does not cache, log, or store any content
- Does not authenticate (relies on `172.17.0.1` being a private Docker bridge address)
- Does not change the model name, system prompt, tools, or any other request field

The only field it writes is `max_tokens` (and `max_completion_tokens` if present), and only
when the model is in `MODEL_TOKENIZER_RATIOS` with a ratio > 1.0.

---

## Measured correction values

| Model | Ratio | Context window | Overflow before fix | Status |
|-------|-------|---------------|---------------------|--------|
| qwen3-next-80b | 1.46 | 262144 | every run at ~5 min | Fixed |
| deepseek-v4-flash | 1.0 | — | never observed | No correction |
