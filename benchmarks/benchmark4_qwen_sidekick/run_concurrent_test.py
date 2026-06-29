#!/usr/bin/env python3
"""
Concurrent test: fire one request at ds4 (port 8000) and one at the sidekick (port 8001)
at the same time, demonstrating they can serve requests in parallel without interfering.

Usage:
  python3 benchmark4_qwen_sidekick/run_concurrent_test.py <out_dir>
"""
import sys
import json
import time
import urllib.request
import threading

DS4_URL = "http://172.17.0.1:8000/v1"
DS4_MODEL = "deepseek-v4-flash"
SIDEKICK_URL = "http://172.17.0.1:8001/v1"
SIDEKICK_MODEL = "qwen3.5-2b"

DS4_PROMPT = "Explain what SSD streaming means in the context of running large language models on hardware with limited RAM. Keep your answer to 2-3 sentences."
SIDEKICK_PROMPT = "What is 17 × 23? Show your working."


def call(base_url, model, prompt, label, results, timeout=300):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode()
        elapsed = time.time() - start
        parsed = json.loads(body)
        content = parsed["choices"][0]["message"]["content"]
        tokens = parsed.get("usage", {}).get("completion_tokens", "?")
        results[label] = {
            "ok": True,
            "elapsed": elapsed,
            "tokens": tokens,
            "preview": content[:200],
            "full": content,
        }
    except Exception as e:
        elapsed = time.time() - start
        results[label] = {"ok": False, "elapsed": elapsed, "error": str(e)}


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "benchmark4_qwen_sidekick/sidekick_results"
    results = {}

    t_ds4 = threading.Thread(target=call, args=(DS4_URL, DS4_MODEL, DS4_PROMPT, "ds4", results))
    t_sk = threading.Thread(target=call, args=(SIDEKICK_URL, SIDEKICK_MODEL, SIDEKICK_PROMPT, "sidekick", results))

    wall_start = time.time()
    print(f"Firing concurrent requests: ds4 @ {DS4_URL}, sidekick @ {SIDEKICK_URL}")
    t_ds4.start()
    t_sk.start()
    t_ds4.join()
    t_sk.join()
    wall_elapsed = time.time() - wall_start

    print(f"\n=== CONCURRENT TEST RESULTS (wall time: {wall_elapsed:.1f}s) ===")
    for label, r in results.items():
        if r["ok"]:
            print(f"\n{label}: elapsed={r['elapsed']:.1f}s tokens={r['tokens']}")
            print(f"  preview: {r['preview']}")
        else:
            print(f"\n{label}: FAILED elapsed={r['elapsed']:.1f}s error={r['error']}")

    with open(f"{out_dir}/concurrent_test.json", "w") as f:
        json.dump({"wall_elapsed": wall_elapsed, "results": results}, f, indent=2)
    print(f"\nSaved to {out_dir}/concurrent_test.json")


if __name__ == "__main__":
    main()
