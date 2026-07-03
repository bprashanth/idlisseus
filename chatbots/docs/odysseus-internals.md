# Idlisseus / Odysseus Internals

Technical notes on how key features work, for maintenance and fork decisions.

## Memory and "Recalled"

### Storage
Single `data/memory.json` containing all users' entries, tagged with an `owner` field.
All users share one file; reads always filter by `owner`. ChromaDB holds the vector
embeddings in a **single shared collection** (`odysseus_memories`) — not partitioned by user.

### Two tiers per request
- **Pinned**: explicitly marked facts (e.g. "my name is X") — injected every turn unconditionally
- **Recalled**: retrieved per-message using BM25 keyword scoring + ChromaDB cosine similarity (fastembed all-MiniLM-L6-v2). Top 3 matches injected as "retrieved context" system message.

The `_hybrid_retrieve` function in `src/chat_processor.py` runs the hybrid scoring:
- BM25 score computed over full memory corpus (IDF from all user's memories)
- Vector score from ChromaDB global query (top k×3 results, filtered back to owner's IDs)
- Recency capped at 5% weight — relevance dominates
- Result is what the "N recalled" badge shows in the UI

### Cross-user isolation gap
ChromaDB `search()` queries the entire collection (all users). Results are filtered back to
the requesting user's IDs after retrieval. This means:
- Other users' memories never leak into your context (ID filter catches it)
- BUT: vector top-k slots are wasted on other users' content; at >50 users, recall quality
  degrades because user-specific results are pushed out of the k-nearest results

**Fix if needed:** add `where={"owner": username}` to the ChromaDB query in
`src/memory_vector.py:search()` — one line change.

### Lifecycle — never auto-cleared
No TTL, no max_entries, no scheduled cleanup. Memories grow forever.
Deleted only by: user manually (Brain panel), admin via API, or user rename
(which triggers `claim_ownerless` migration for legacy ownerless entries).

Memory is extracted automatically at end of conversation: `memory_extractor.py` runs an LLM
pass over the transcript to pull out facts worth keeping, deduplicates via vector similarity
(threshold 0.72), then writes to `memory.json` and indexes in ChromaDB.

---

## Deep Research

### The loop
IterResearch-inspired (`src/deep_research.py`, ~930 lines). Each round:
1. **THINK**: LLM generates search queries given the question + current report state
2. **SEARCH**: SearXNG (async, multiple queries in parallel)
3. **EXTRACT**: LLM extracts relevant facts from each page
4. **SYNTHESIZE**: LLM rewrites the evolving report incorporating new findings
5. **DECIDE**: LLM answers YES/NO "is this comprehensive enough?"

The loop is **LLM-driven within framework hard stops**:

| Condition | Who decides | Default |
|-----------|------------|---------|
| "Is this complete?" | LLM (YES/NO after `min_rounds`) | After round 2 |
| Max rounds | Framework | 8 |
| Wall-clock timeout | Framework | 300s |
| Empty results × N | Framework | 2 consecutive |
| No queries generated | Framework | immediate break |
| User cancellation | UI event → `_cancelled` flag | on demand |

In practice: LLM typically stops at round 3–5 for well-covered topics.
At 3–20s per LLM call and several calls per round, the 300s timeout is the real practical cap.

### Images in the report
**Not AI-generated.** They are `og:image` metadata tags scraped from web pages during
search. DeepResearcher collects them in `section_pool`; `visual_report.py` injects them
after `</h2>` headings. There's a "reroll" pool of unused images (UI lets users swap or hide).
Quality entirely depends on source pages' featured images.

### Report persistence
Each report: a JSON file in `data/deep_research/{session_id}.json`. No TTL, no cleanup.
Served at `/api/research/report/{session_id}` as a full standalone HTML page with embedded
CSS, scroll-spy JS, and image controls. Accessible as long as the `data/` volume exists.

---

## Explain Simpler / Shorter buttons

Call `POST /api/rewrite` — a **lightweight endpoint completely separate from the agent loop**:
- Input: `original_text` (the AI message content) + `instruction` string
- System prompt: "Output ONLY the rewritten text — no preamble, no explanation."
- 2-message exchange only (system + original + instruction) — no history, no tools
- Streams the rewrite back; **replaces the original message** in UI and session history
- "Explain Simpler" instruction: `"Explain your last response in simpler terms. Use plain language and short sentences."`
- "Shorter" instruction: `"Rewrite your last response to be shorter and more concise."`

Much faster than a full chat round. Reasoning model `<think>` output is stripped before saving.

---

## Agent mode vs Hermes

Odysseus's agent loop (`src/agent_loop.py`) handles two formats:
1. **OpenAI-native tool_calls** — when 80B emits proper tool_call objects via vLLM's
   `--tool-call-parser hermes`. This is the active path.
2. **Fenced code blocks** — fallback for models that don't emit structured tool_calls.

Tool execution (`src/tool_execution.py`) runs `bash`/`python` as real subprocesses inside
the container. No additional sandbox beyond the container boundary. Background jobs marked
`#!bg` run async.

Hermes (token proxy in `agents/hermes/`) is now redundant for 80B — vLLM handles the
tool_call format natively. Hermes is useful only if switching back to ds4 or another
model that doesn't natively support tool_calls.

Spiral limits (our additions):
- `agent_max_tool_calls = 20` (was 0, unlimited) — `src/settings.py`
- `_WEB_SEARCH_CAP = 5` per turn + duplicate query detection — `src/agent_loop.py`
