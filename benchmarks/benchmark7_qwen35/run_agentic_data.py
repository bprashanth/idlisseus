#!/usr/bin/env python3
"""
Data-finding agentic loop: 122B searches the internet (via SearXNG→Google/Startpage),
finds CSVs/Excels, downloads them, and extracts insights using pandas.

Tools:
  web_search(query, filetype?)  — SearXNG JSON API (real Google/Startpage results)
  fetch_url(url)                — HTML→text, PDF→pdftotext, CSV/XLS→pandas summary
  read_data(url)                — explicit data file download + analysis (pandas)

Task: find forest fire incident data for India, download, extract key statistics.
Compare against B2 ds4-agent which downloaded 20 PDFs in 25min.
"""

import sys, json, time, re, os, urllib.request, urllib.parse, subprocess
import tempfile, io
import pandas as pd

URL   = "http://172.17.0.1:8001/v1"
MODEL = "qwen"
SEARX = "http://127.0.0.1:8080"
OUT   = sys.argv[1] if len(sys.argv) > 1 else "/tmp/agentic_data_result.json"

# ── Tool implementations ─────────────────────────────────────────────────────

def web_search(query: str, filetype: str = "") -> str:
    """Search via SearXNG (Google + Startpage backends). filetype: csv, xlsx, pdf, etc."""
    try:
        full_query = f"{query} filetype:{filetype}" if filetype else query
        q = urllib.parse.quote(full_query)
        url = f"{SEARX}/search?q={q}&format=json&language=en"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
        results = data.get("results", [])
        if not results:
            return f"No results found for: {full_query}"
        engines = set(e for r in results for e in r.get("engines", []))
        lines = [f"web_search: {len(results)} results via {', '.join(engines)}\n"]
        for i, r in enumerate(results[:8], 1):
            title   = r.get("title", "?")[:60]
            rurl    = r.get("url", "?")
            snippet = (r.get("content") or "")[:120].replace("\n", " ")
            lines.append(f"[{i}] {title}\n    {rurl}\n    {snippet}")
        return "\n".join(lines)
    except Exception as e:
        return f"web_search error: {e}"


def _is_data_url(url: str) -> bool:
    return any(url.lower().endswith(ext) for ext in
               (".csv", ".xlsx", ".xls", ".tsv", ".json", ".geojson", ".parquet"))


def read_data(url: str) -> str:
    """Download a CSV/Excel/TSV and return a pandas summary (shape, dtypes, head, stats)."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            ct = r.headers.get("Content-Type", "").lower()
            raw = r.read()

        url_lower = url.lower()
        if url_lower.endswith(".xlsx") or url_lower.endswith(".xls") or "spreadsheet" in ct:
            df = pd.read_excel(io.BytesIO(raw), nrows=200)
        elif url_lower.endswith(".tsv"):
            df = pd.read_csv(io.StringIO(raw.decode("utf-8", errors="replace")),
                             sep="\t", nrows=200, on_bad_lines="skip")
        else:
            # try CSV
            try:
                df = pd.read_csv(io.StringIO(raw.decode("utf-8", errors="replace")),
                                 nrows=200, on_bad_lines="skip")
            except Exception:
                df = pd.read_csv(io.StringIO(raw.decode("latin-1", errors="replace")),
                                 nrows=200, on_bad_lines="skip")

        lines = [
            f"[Data file: {url.split('/')[-1]}]",
            f"Shape: {df.shape[0]} rows × {df.shape[1]} cols",
            f"Columns: {list(df.columns)}",
            f"\nDtypes:\n{df.dtypes.to_string()}",
            f"\nFirst 3 rows:\n{df.head(3).to_string()}",
        ]
        num_cols = df.select_dtypes("number")
        if not num_cols.empty:
            lines.append(f"\nNumeric summary:\n{num_cols.describe().round(2).to_string()}")
        null_counts = df.isnull().sum()
        if null_counts.any():
            lines.append(f"\nNull counts: {null_counts[null_counts > 0].to_string()}")
        return "\n".join(lines)
    except Exception as e:
        return f"read_data error for {url}: {e}"


def fetch_url(url: str) -> str:
    """Fetch a URL. Data files → read_data(). PDFs → pdftotext. HTML → stripped text."""
    if _is_data_url(url):
        return read_data(url)
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            ct = r.headers.get("Content-Type", "").lower()
            raw = r.read()

        if "pdf" in ct or url.lower().endswith(".pdf"):
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(raw)
                tmp = f.name
            try:
                res = subprocess.run(["pdftotext", "-l", "5", tmp, "-"],
                                     capture_output=True, text=True, timeout=30)
                text = res.stdout.strip()
                return f"[PDF, {len(text)} chars]\n{text[:3000]}" if text else \
                       f"[PDF downloaded {len(raw)}B but pdftotext empty — likely scanned]"
            finally:
                os.unlink(tmp)

        if "csv" in ct or "excel" in ct or "spreadsheet" in ct:
            return read_data(url)

        html = raw.decode("utf-8", errors="replace")
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:3000]
    except Exception as e:
        return f"fetch_url error: {e}"


def dispatch(tool: str, args: dict) -> str:
    if tool == "web_search":
        return web_search(args.get("query", ""), args.get("filetype", ""))
    elif tool == "fetch_url":
        return fetch_url(args.get("url", ""))
    elif tool == "read_data":
        return read_data(args.get("url", ""))
    return f"Unknown tool: {tool}"


def parse_tool_calls(text: str):
    return re.findall(r"TOOL_CALL:\s*(\w+)\s*\nARGS:\s*(\{[^\n]+\})", text)


# ── Agentic loop ─────────────────────────────────────────────────────────────

SYSTEM = """You are a data research assistant. Find datasets on the internet, download them,
and extract statistical insights. You have access to real Google/web search.

Available tools (use EXACTLY this format, one per turn):
  TOOL_CALL: web_search
  ARGS: {"query": "your query here", "filetype": "csv"}

  TOOL_CALL: fetch_url
  ARGS: {"url": "https://..."}

  TOOL_CALL: read_data
  ARGS: {"url": "https://path/to/file.csv"}

Rules:
- Start with web_search to find relevant datasets (use filetype: csv or xlsx to find data files)
- Use read_data directly on CSV/Excel URLs — it downloads and gives you shape, columns, stats
- Use fetch_url for HTML pages, PDFs, or data files
- If a URL returns an error, note it and try the next one
- After finding and analysing 2-3 datasets, write your final report
- The report must include: source URL, file shape, key columns, and 3+ concrete statistical findings per dataset
- Be specific: cite actual numbers from the data, not vague observations
- End with a markdown table comparing key metrics across datasets"""

TASK = sys.argv[2] if len(sys.argv) > 2 else (
    "Find structured datasets (CSV or Excel) on forest fire incidents in India. "
    "Download the actual data files, analyse them with statistics, and report: "
    "which states/regions have the most fires, what time trends exist, "
    "and any correlations with area or season. Be specific with numbers."
)

MAX_TURNS = 14

def run():
    messages = [{"role": "user", "content": TASK}]
    tool_log = []
    data_files_read = []
    t_start = time.time()

    print(f"Task: {TASK}")
    print(f"Model: {MODEL}  SearXNG: {SEARX}  Max turns: {MAX_TURNS}\n")

    for turn in range(MAX_TURNS):
        # At 75% of budget, inject a synthesis nudge if no data read yet OR if many turns spent
        if turn == MAX_TURNS * 3 // 4 and not data_files_read:
            messages.append({
                "role": "user",
                "content": ("You have used most of your search budget. Write your final report now "
                            "based on everything found so far, even if the data is imperfect. "
                            "Be specific about what you could and could not find.")
            })

        payload = {
            "model": MODEL,
            "messages": [{"role": "system", "content": SYSTEM}] + messages,
            "max_tokens": 2048,
            "temperature": 0.2,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            URL + "/chat/completions", data=data,
            headers={"Content-Type": "application/json"}
        )
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.load(r)
        elapsed = time.time() - t0

        choice  = d["choices"][0]
        content = choice["message"].get("content") or ""
        finish  = choice.get("finish_reason", "")
        tc_list = parse_tool_calls(content)

        print(f"Turn {turn+1:2d}: {elapsed:4.0f}s | finish={finish} | tool_calls={len(tc_list)} | {len(content)}c")
        messages.append({"role": "assistant", "content": content})

        if not tc_list:
            print("  → No tool calls — writing final answer.")
            break

        for tool_name, args_str in tc_list:
            try:
                args = json.loads(args_str)
            except Exception:
                args = {}
            preview = json.dumps(args)[:80]
            print(f"  → {tool_name}({preview})")
            t_tool = time.time()
            result = dispatch(tool_name, args)
            tool_elapsed = time.time() - t_tool
            result_preview = result[:120].replace("\n", " ")
            print(f"     {tool_elapsed:.1f}s → {len(result)}c: {result_preview}")
            tool_log.append({
                "turn": turn + 1, "tool": tool_name, "args": args,
                "result_len": len(result), "tool_elapsed_s": round(tool_elapsed, 1),
            })
            if tool_name in ("read_data", "fetch_url") and "Shape:" in result:
                data_files_read.append(args.get("url", ""))
            messages.append({
                "role": "user",
                "content": f"TOOL_RESULT for {tool_name}:\n{result}"
            })
            break  # one tool call per turn

    wall = time.time() - t_start
    final = next(
        (m["content"] for m in reversed(messages)
         if m.get("role") == "assistant" and m.get("content")
         and not parse_tool_calls(m["content"])),
        ""
    )

    print(f"\nDone: {wall:.0f}s | {turn+1} turns | {len(tool_log)} tools | {len(data_files_read)} data files read")
    print(f"Data files: {data_files_read}")
    print(f"\nFinal answer ({len(final)} chars):\n{'='*72}")
    print(final)
    print("="*72)

    with open(OUT, "w") as f:
        json.dump({
            "task": TASK, "wall_s": round(wall, 1), "turns": turn + 1,
            "tool_log": tool_log, "data_files_read": data_files_read,
            "final_answer": final, "messages": messages,
        }, f, indent=2)
    print(f"\nSaved: {OUT}")


if __name__ == "__main__":
    run()
