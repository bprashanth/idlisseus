#!/usr/bin/env python3
"""Run one benchmark-3 task against a given model/endpoint, save prompt+response, print timing."""
import sys
import json
import time
import urllib.request

PAPERS_DIR = "/home/beeps/src/github.com/bprashanth/idlisseus/benchmark3_seed_oss/papers"


def read(name):
    with open(f"{PAPERS_DIR}/{name}") as f:
        return f.read()


def build_prompt(task):
    if task == "1":
        return (
            "Summarize the following paper in about 3 paragraphs.\n\n"
            f"=== 03_Forest_Fire_Himalayan_Regions ===\n{read('03_Forest_Fire_Himalayan_Regions.txt')}"
        )
    if task == "2":
        docs = ["01_Models_Forest_Fire_Management_India", "03_Forest_Fire_Himalayan_Regions",
                "09_Wildfire_Burn_Severity_Uttarakhand", "11_Cloud_Based_Fire_Alert_IoT",
                "16_Madhuca_Longifolia_Fire_Cause"]
        body = "\n\n".join(f"=== {d} ===\n{read(d + '.txt')}" for d in docs)
        return (
            "Below are 5 papers on forest fire / wildfire management. Identify: (a) what these "
            "papers agree on, (b) any real disagreements between them (be specific about which "
            "paper says what), and (c) what each paper's main contribution is. Cite papers by "
            "their document name (e.g. '01_Models_Forest_Fire_Management_India').\n\n" + body
        )
    if task == "3":
        docs = ["01_Models_Forest_Fire_Management_India", "16_Madhuca_Longifolia_Fire_Cause"]
        body = "\n\n".join(f"=== {d} ===\n{read(d + '.txt')}" for d in docs)
        return (
            "Based ONLY on the two papers below: what do they say about the causes of forest "
            "fires, and do they agree or disagree on the relative importance of any specific "
            "cause? If something is not stated in either paper, say so explicitly rather than "
            "guessing.\n\n" + body
        )
    if task == "4":
        docs = ["01_Models_Forest_Fire_Management_India", "03_Forest_Fire_Himalayan_Regions",
                "09_Wildfire_Burn_Severity_Uttarakhand", "11_Cloud_Based_Fire_Alert_IoT",
                "16_Madhuca_Longifolia_Fire_Cause"]
        body = "\n\n".join(f"=== {d} ===\n{read(d + '.txt')}" for d in docs)
        return (
            "Below are 5 papers on forest fire / wildfire management. Produce a single, complete, "
            "self-contained dashboard.html file (inline CSS/JS, no external dependencies) that "
            "visually summarizes: key themes across the papers, any disagreements you find, and "
            "a simple chart of paper topics. Output ONLY the HTML file content, nothing else.\n\n"
            + body
        )
    raise ValueError(task)


def call(base_url, model, prompt, stream=False, max_tokens=None):
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": stream}
    if max_tokens:
        payload["max_tokens"] = max_tokens
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{base_url}/chat/completions", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    start = time.time()
    with urllib.request.urlopen(req, timeout=3600) as resp:
        body = resp.read().decode()
    elapsed = time.time() - start
    return body, elapsed


def main():
    task = sys.argv[1]
    base_url = sys.argv[2]
    model = sys.argv[3]
    out_dir = sys.argv[4]
    prompt = build_prompt(task)
    body, elapsed = call(base_url, model, prompt)
    with open(f"{out_dir}/task{task}_prompt.txt", "w") as f:
        f.write(prompt)
    with open(f"{out_dir}/task{task}_response.json", "w") as f:
        f.write(body)
    try:
        parsed = json.loads(body)
        content = parsed["choices"][0]["message"]["content"]
        usage = parsed.get("usage", {})
        with open(f"{out_dir}/task{task}_response.txt", "w") as f:
            f.write(content)
        print(f"task {task}: elapsed={elapsed:.1f}s usage={usage}")
    except Exception as e:
        print(f"task {task}: elapsed={elapsed:.1f}s PARSE_ERROR={e}")
        print(body[:500])


if __name__ == "__main__":
    main()
