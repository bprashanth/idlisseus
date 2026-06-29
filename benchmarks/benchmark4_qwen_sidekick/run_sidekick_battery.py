#!/usr/bin/env python3
"""
Light benchmark battery for Stage 2 sidekick (Qwen3.5-2B on port 8001).
~5-6 short prompts only — short queries, wordsmithing, one-paragraph summaries,
arithmetic, structured-output. No large documents.

Usage:
  python3 benchmark4_qwen_sidekick/run_sidekick_battery.py \
      http://172.17.0.1:8001/v1 qwen3.5-2b benchmark4_qwen_sidekick/sidekick_results
"""
import sys
import json
import time
import urllib.request

TASKS = {
    "1": {
        "name": "short_query",
        "prompt": "What are the three main types of forest fire (ground, surface, and crown)? Give a one-sentence description of each.",
    },
    "2": {
        "name": "wordsmithing",
        "prompt": (
            "Rewrite the following sentence to be more concise and professional, "
            "keeping the same meaning:\n\n"
            "\"Due to the fact that there was a significant amount of rainfall during "
            "the month of June, the fire risk index for the region was observed to be "
            "at a notably lower level than what is typically seen during this time of year.\""
        ),
    },
    "3": {
        "name": "short_summary",
        "prompt": (
            "Summarize the following paragraph in one sentence:\n\n"
            "\"Community-based fire management (CBFM) programs in the Nilgiris have "
            "demonstrated measurable reductions in annual burned area when villages "
            "participate in joint monitoring and controlled burning schedules. Unlike "
            "top-down suppression strategies, CBFM leverages traditional ecological "
            "knowledge held by local Toda and Irula communities, integrating seasonal "
            "fire calendars with modern remote-sensing alerts. Evaluations from 2015 "
            "to 2022 show that CBFM villages experienced 34% fewer uncontrolled fire "
            "events compared to control sites, though data gaps in the earlier years "
            "make before-after comparisons difficult to interpret with high confidence.\""
        ),
    },
    "4": {
        "name": "arithmetic",
        "prompt": (
            "A forest patch burned at a rate of 12 hectares per hour for 3.5 hours, "
            "then the rate doubled for another 2 hours. How many total hectares burned? "
            "Show your working."
        ),
    },
    "5": {
        "name": "structured_output",
        "prompt": (
            "You are a data extraction assistant. Extract the following fields from "
            "the incident report below and return them as valid JSON only "
            "(no markdown fences, no explanation):\n"
            "  incident_date, location, fire_type, area_ha, cause, suppressed_by\n\n"
            "Report: \"On 14 March 2024, forest rangers recorded a surface fire in "
            "the Mudumalai Tiger Reserve near Theppakadu, covering approximately "
            "27 hectares. The fire was attributed to a discarded cigarette along "
            "a tourist trail and was suppressed by the Tamil Nadu Forest Department "
            "rapid response team within 6 hours.\""
        ),
    },
    "6": {
        "name": "translation_short",
        "prompt": (
            "Translate the following sentence from English to Hindi:\n\n"
            "\"Early detection of forest fires saves lives and protects biodiversity.\""
        ),
    },
}


def call(base_url, model, prompt, timeout=120):
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
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode()
    elapsed = time.time() - start
    return body, elapsed


def main():
    if len(sys.argv) != 4:
        print("Usage: run_sidekick_battery.py <base_url> <model> <out_dir>")
        sys.exit(1)
    base_url, model, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]

    summary_rows = []
    for task_id in sorted(TASKS):
        task = TASKS[task_id]
        name = task["name"]
        prompt = task["prompt"]
        print(f"\n--- Task {task_id} ({name}) ---")
        print(f"Prompt: {prompt[:120]}{'...' if len(prompt) > 120 else ''}")

        try:
            body, elapsed = call(base_url, model, prompt)
            parsed = json.loads(body)
            content = parsed["choices"][0]["message"]["content"]
            usage = parsed.get("usage", {})
            completion_tokens = usage.get("completion_tokens", "?")
            tok_per_sec = (
                completion_tokens / elapsed if isinstance(completion_tokens, int) else "?"
            )

            with open(f"{out_dir}/task{task_id}_{name}_prompt.txt", "w") as f:
                f.write(prompt)
            with open(f"{out_dir}/task{task_id}_{name}_response.txt", "w") as f:
                f.write(content)
            with open(f"{out_dir}/task{task_id}_{name}_response.json", "w") as f:
                f.write(body)

            print(f"Response ({elapsed:.1f}s, {completion_tokens} tokens, "
                  f"{tok_per_sec:.1f} tok/s if known):")
            print(content[:300] + ("..." if len(content) > 300 else ""))
            summary_rows.append(
                f"| {task_id} | {name} | {elapsed:.1f}s | {completion_tokens} tokens | OK |"
            )
        except Exception as e:
            print(f"ERROR: {e}")
            summary_rows.append(f"| {task_id} | {name} | — | — | ERROR: {e} |")

    print("\n\n=== SUMMARY ===")
    print("| Task | Name | Elapsed | Tokens | Status |")
    print("|------|------|---------|--------|--------|")
    for row in summary_rows:
        print(row)

    with open(f"{out_dir}/summary.md", "w") as f:
        f.write("# Sidekick Battery Summary (Stage 2)\n\n")
        f.write("Model: qwen3.5-2b on port 8001, alongside ds4 on port 8000\n\n")
        f.write("| Task | Name | Elapsed | Tokens | Status |\n")
        f.write("|------|------|---------|--------|--------|\n")
        for row in summary_rows:
            f.write(row + "\n")

    print(f"\nOutputs saved to {out_dir}/")


if __name__ == "__main__":
    main()
