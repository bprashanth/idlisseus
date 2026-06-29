#!/usr/bin/env python3
"""hermes-token-proxy: thin HTTP proxy that corrects max_tokens for models whose
tokenizers produce more tokens than Hermes estimates.

Background:
    Hermes Agent estimates token counts at ~4 chars/token when computing the output budget
    it can request (max_tokens = context_window - estimated_prompt_tokens).  Models with
    BPE-heavy tokenizers produce more tokens per character than this estimate.  The result:
    actual_prompt_tokens > estimated, so actual_prompt + max_tokens > context_window, and
    vLLM returns HTTP 400.

    Measured ratio for Qwen3-Next-80B-A3B-Instruct-FP8: 1.46 (46% more tokens than Hermes
    estimates).  ds4-flash is close enough to 1.0 that no correction is needed.

Fix:
    Intercept POST /v1/chat/completions.  For models in MODEL_TOKENIZER_RATIOS, divide
    max_tokens by the ratio before forwarding.  This shrinks the output budget so there is
    room for the underestimated prompt.  Everything else (headers, streaming, other paths)
    passes through unchanged.

    Derivation: if Hermes estimates prompt_est and requests max_tokens = C - prompt_est,
    but actual_prompt = ratio * prompt_est, then safe_max = C - ratio * prompt_est.
    Substituting: safe_max ≈ max_tokens / ratio (conservative; gives ~30% extra headroom
    beyond the theoretical minimum).

Deployment:
    Run as a systemd service (see deploy/hermes/hermes-token-proxy.service).
    Listens on 172.17.0.1:8001, forwards to vLLM on 172.17.0.1:8000.
    Point Hermes at http://172.17.0.1:8001/v1 instead of :8000.

    When the running model is not in MODEL_TOKENIZER_RATIOS (e.g. ds4-flash), this proxy
    is a transparent passthrough -- ratio defaults to 1.0, nothing is changed.
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests as _requests

UPSTREAM = "http://172.17.0.1:8000"
LISTEN_HOST = "172.17.0.1"
LISTEN_PORT = 8001

# Measured actual_tokens / hermes_estimated_tokens for each served model name.
# 1.0 = no correction.  Add entries here as new models are characterised.
MODEL_TOKENIZER_RATIOS: dict[str, float] = {
    "qwen3-next-80b": 1.46,
}

MIN_MAX_TOKENS = 4096  # never shrink the budget below this


def _correct_body(raw: bytes) -> bytes:
    try:
        body = json.loads(raw)
    except Exception:
        return raw

    ratio = MODEL_TOKENIZER_RATIOS.get(body.get("model", ""), 1.0)
    if ratio == 1.0:
        return raw

    changed = False
    for field in ("max_tokens", "max_completion_tokens"):
        if field in body and isinstance(body[field], int) and body[field] > MIN_MAX_TOKENS:
            original = body[field]
            body[field] = max(MIN_MAX_TOKENS, int(original / ratio))
            print(
                f"[token-proxy] {body.get('model')} {field}: {original} → {body[field]}"
                f"  (ratio={ratio})",
                flush=True,
            )
            changed = True

    return json.dumps(body).encode() if changed else raw


class _ProxyHandler(BaseHTTPRequestHandler):
    def _dispatch(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""

        if self.path.strip("/") == "v1/chat/completions" and body:
            body = _correct_body(body)

        # Forward headers, dropping hop-by-hop fields we'll re-set ourselves.
        skip = {"host", "content-length", "transfer-encoding", "connection"}
        headers = {k: v for k, v in self.headers.items() if k.lower() not in skip}
        if body:
            headers["Content-Length"] = str(len(body))

        url = UPSTREAM + self.path
        resp = _requests.request(
            method=self.command,
            url=url,
            headers=headers,
            data=body,
            stream=True,
            timeout=None,
        )

        self.send_response(resp.status_code)
        skip_resp = {"transfer-encoding", "content-length", "connection"}
        for k, v in resp.headers.items():
            if k.lower() not in skip_resp:
                self.send_header(k, v)
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

        for chunk in resp.iter_content(chunk_size=4096):
            if chunk:
                self.wfile.write(f"{len(chunk):x}\r\n".encode())
                self.wfile.write(chunk)
                self.wfile.write(b"\r\n")
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()

    do_GET = do_POST = do_PUT = do_DELETE = do_OPTIONS = do_HEAD = do_PATCH = _dispatch

    def log_message(self, fmt, *args) -> None:  # silence default access log
        pass


if __name__ == "__main__":
    server = HTTPServer((LISTEN_HOST, LISTEN_PORT), _ProxyHandler)
    print(
        f"[token-proxy] Listening on {LISTEN_HOST}:{LISTEN_PORT}, "
        f"upstream: {UPSTREAM}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[token-proxy] Stopped.", flush=True)
