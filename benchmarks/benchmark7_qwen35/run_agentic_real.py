#!/usr/bin/env python3
"""
Real agentic loop: 122B finds papers on its own using Zenodo + CrossRef APIs.

Tools exposed to the model:
  zenodo_search(query, size)   — full-text search against Zenodo API (returns title/authors/year/DOI/abstract)
  crossref_search(query, rows) — CrossRef works search (returns title/authors/year/DOI)
  fetch_url(url)               — fetch any URL; if it looks like a PDF, download + pdftotext

Compare against B2 ds4-agent: 20 real PDFs, 25 min, specific citations, found gaps honestly.
"""

import sys, json, time, re, os, urllib.request, urllib.parse, subprocess, tempfile

URL   = "http://172.17.0.1:8001/v1"
MODEL = "qwen"
OUT   = sys.argv[1] if len(sys.argv) > 1 else "/tmp/agentic_real_result.json"

# ── Tool implementations ────────────────────────────────────────────────────

def zenodo_search(query: str, size: int = 5) -> str:
    """Search Zenodo for academic publications."""
    try:
        q = urllib.parse.quote(query)
        api = f"https://zenodo.org/api/records?q={q}&size={size}&type=publication&sort=mostrecent"
        req = urllib.request.Request(api, headers={"User-Agent": "benchmark7/1.0 (research)"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
        hits = data.get("hits", {}).get("hits", [])
        if not hits:
            return "No results found on Zenodo for this query."
        lines = [f"Zenodo search: {len(hits)} results for '{query}'\n"]
        for i, h in enumerate(hits, 1):
            m = h.get("metadata", {})
            title   = m.get("title", "?")
            authors = ", ".join(c.get("name", "?") for c in m.get("creators", [])[:3])
            year    = (m.get("publication_date") or "")[:4]
            doi     = m.get("doi", "")
            desc    = (m.get("description") or "")[:300].replace("\n", " ")
            rec_id  = h.get("id", "")
            files   = h.get("files", [])
            pdf_fn  = next((f["key"] for f in files if f["key"].lower().endswith(".pdf")), None)
            pdf_url = (f"https://zenodo.org/records/{rec_id}/files/{urllib.parse.quote(pdf_fn)}"
                       if pdf_fn else "no-pdf")
            lines.append(
                f"[{i}] {title}\n"
                f"    Authors: {authors}\n"
                f"    Year: {year}  DOI: {doi}\n"
                f"    PDF: {pdf_url}\n"
                f"    Abstract: {desc}...\n"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"zenodo_search error: {e}"


def crossref_search(query: str, rows: int = 5) -> str:
    """Search CrossRef for papers by metadata."""
    try:
        q = urllib.parse.quote(query)
        api = (f"https://api.crossref.org/works?query={q}&rows={rows}"
               f"&select=DOI,title,author,published,abstract"
               f"&mailto=research@idlisseus.org")
        req = urllib.request.Request(api, headers={"User-Agent": "benchmark7/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
        items = data.get("message", {}).get("items", [])
        if not items:
            return "No results found on CrossRef for this query."
        lines = [f"CrossRef search: {len(items)} results for '{query}'\n"]
        for i, item in enumerate(items, 1):
            title   = " ".join(item.get("title", ["?"])[:1])
            authors = ", ".join(
                f"{a.get('family','')}, {a.get('given','')}"
                for a in item.get("author", [])[:3]
            )
            pub     = item.get("published", {}).get("date-parts", [[""]])[0]
            year    = str(pub[0]) if pub else "?"
            doi     = item.get("DOI", "")
            abstract = (item.get("abstract") or "")[:300].replace("\n", " ")
            doi_url = f"https://doi.org/{doi}" if doi else "no-doi"
            lines.append(
                f"[{i}] {title}\n"
                f"    Authors: {authors}\n"
                f"    Year: {year}  DOI: {doi}\n"
                f"    URL: {doi_url}\n"
                f"    Abstract: {abstract}...\n"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"crossref_search error: {e}"


def fetch_url(url: str) -> str:
    """Fetch a URL. PDFs are extracted with pdftotext; HTML pages are stripped."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            content_type = r.headers.get("Content-Type", "")
            raw = r.read()

        if "pdf" in content_type.lower() or url.lower().endswith(".pdf"):
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(raw)
                tmp = f.name
            try:
                result = subprocess.run(
                    ["pdftotext", "-l", "8", tmp, "-"],  # first 8 pages
                    capture_output=True, text=True, timeout=30
                )
                text = result.stdout.strip()
                if not text:
                    return f"PDF downloaded ({len(raw)} bytes) but pdftotext returned empty — may be scanned."
                return f"[PDF extract, first 8 pages, {len(text)} chars]\n{text[:4000]}"
            finally:
                os.unlink(tmp)
        else:
            html = raw.decode("utf-8", errors="replace")
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:3000]
    except Exception as e:
        return f"fetch_url error: {e}"


# ── Tool dispatch ────────────────────────────────────────────────────────────

def dispatch(tool: str, args: dict) -> str:
    if tool == "zenodo_search":
        return zenodo_search(args.get("query", ""), int(args.get("size", 5)))
    elif tool == "crossref_search":
        return crossref_search(args.get("query", ""), int(args.get("rows", 5)))
    elif tool == "fetch_url":
        return fetch_url(args.get("url", ""))
    return f"Unknown tool: {tool}"


# ── Tool-format parser ───────────────────────────────────────────────────────

def parse_tool_calls(text: str):
    """Extract TOOL_CALL / ARGS blocks from model output."""
    return re.findall(r"TOOL_CALL:\s*(\w+)\s*\nARGS:\s*(\{[^\n]+\})", text)


# ── Agentic loop ─────────────────────────────────────────────────────────────

SYSTEM = """You are a research assistant with access to academic databases. Your goal is to find
real papers on a research topic, read them, and synthesise the findings.

Available tools (use EXACTLY this format, one tool call per turn):
  TOOL_CALL: zenodo_search
  ARGS: {"query": "your search query", "size": 5}

  TOOL_CALL: crossref_search
  ARGS: {"query": "your search query", "rows": 5}

  TOOL_CALL: fetch_url
  ARGS: {"url": "https://..."}

Rules:
- Start with zenodo_search to find papers in your topic area.
- Use crossref_search if you need to broaden the search.
- Use fetch_url with the PDF URL from Zenodo to read a paper's full text.
- If fetch_url fails, note it and move on — don't retry the same URL.
- When you have read at least 3-4 papers, stop calling tools and write your final report.
- The final report must include: per-paper (title, authors, year, 2-sentence summary) and
  a synthesis section noting agreements, disagreements, and gaps in the literature.
- End the report with a markdown table: Paper | Year | Key Finding.
- Do NOT use DuckDuckGo or general web search — use zenodo_search and crossref_search only."""

TASK = ("Find 4-6 recent papers on forest fire management in India or the Himalayas. "
        "Read their full text where possible, then write a synthesis report with an HTML table.")

MAX_TURNS = 12

def run():
    messages = [{"role": "user", "content": TASK}]
    tool_log = []
    total_wall = 0.0
    papers_fetched = []
    t_start = time.time()

    print(f"Task: {TASK}")
    print(f"Model: {MODEL}  Max turns: {MAX_TURNS}\n")

    for turn in range(MAX_TURNS):
        payload = {
            "model": MODEL,
            "messages": [{"role": "system", "content": SYSTEM}] + messages,
            "max_tokens": 1536,
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
        total_wall += elapsed

        choice  = d["choices"][0]
        content = choice["message"].get("content") or ""
        finish  = choice.get("finish_reason", "")

        tc_list = parse_tool_calls(content)
        print(f"Turn {turn+1:2d}: {elapsed:4.0f}s | finish={finish} | tool_calls={len(tc_list)} | {len(content)}c")

        messages.append({"role": "assistant", "content": content})

        if not tc_list:
            print("  → No tool calls — model is writing final answer.")
            break

        for tool_name, args_str in tc_list:
            try:
                args = json.loads(args_str)
            except Exception:
                args = {}
            preview = json.dumps(args)[:70]
            print(f"  → {tool_name}({preview})")
            t_tool = time.time()
            result = dispatch(tool_name, args)
            tool_elapsed = time.time() - t_tool
            print(f"     result: {len(result)} chars in {tool_elapsed:.1f}s")
            tool_log.append({
                "turn": turn + 1,
                "tool": tool_name,
                "args": args,
                "result_len": len(result),
                "tool_elapsed_s": round(tool_elapsed, 1),
            })
            if tool_name == "fetch_url" and "[PDF extract" in result:
                papers_fetched.append(args.get("url", ""))
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

    print(f"\nDone: {wall:.0f}s total | {turn+1} turns | {len(tool_log)} tool calls | {len(papers_fetched)} PDFs read")
    print(f"Final answer: {len(final)} chars")
    print("\n" + "="*72)
    print(final)
    print("="*72)

    with open(OUT, "w") as f:
        json.dump({
            "task": TASK,
            "wall_s": round(wall, 1),
            "turns": turn + 1,
            "tool_log": tool_log,
            "pdfs_fetched": papers_fetched,
            "final_answer": final,
            "messages": messages,
        }, f, indent=2)
    print(f"\nSaved: {OUT}")


if __name__ == "__main__":
    run()
