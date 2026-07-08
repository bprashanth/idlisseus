# Trace introspection — how the agent can study (and improve) itself

Every Hermes session leaves a full, queryable record inside the persistent container. Reading it back is
the cheapest way we have to find where the agent went wrong and turn that into a durable fix — the
concrete engine behind the MASTER_PLAN's **Miner** ("logs → PLAYBOOK rules") and the
[`semantic_broker/LIMITATIONS.md`](../../benchmarks/semantic_broker/LIMITATIONS.md) register.

## The three record stores (container `hermes-live`, under `/opt/data` = host `~/.hermes`)

| Store | Path | What it holds | Use it for |
|---|---|---|---|
| **`state.db`** (SQLite) | `/opt/data/state.db` | **The full transcript**: every user/assistant/tool message | *what was actually said/answered* — the ground truth for a review |
| **`agent.log`** | `/opt/data/logs/agent.log` | Per-call **metadata**: turn_context (the user msg), API call #, in/out tokens, latency, tool char-counts, turn-end reason | *shape of a session* — how many calls/tools, where it stalled, which turn ran no tools |
| **tirith policy log** (JSONL) | `/opt/data/.local/share/tirith/log.jsonl` | Every shell/tool command + Allow/Deny verdict (redacted args) | *what commands ran* — which connectors, in what order, what was denied |

`state.db` is the important one; the other two are fast indexes into it.

### `state.db` schema (the parts that matter)
- **`sessions`** — one row per session (id, `last_message_at`, `message_count`).
- **`messages`** — the transcript. Key columns:
  `id, session_id, role, content, tool_call_id, tool_calls, tool_name, timestamp, token_count,
  finish_reason, reasoning, reasoning_content, active, compacted`.
  - `role` ∈ user / assistant / tool. `content` = the text (assistant answers, tool *results*, user asks).
  - `tool_calls` / `tool_name` / `tool_call_id` tie an assistant tool-call to its `tool` result row.
  - `reasoning*` = the model's thinking (when present). `compacted`/`active` = compression bookkeeping.
- **`messages_fts`** (+ trigram) — FTS5 full-text index over `content` → keyword search across all sessions.

## Recipes

```bash
# session ids do NOT auto-attach to a shell; run these inside the container:
DB=/opt/data/state.db

# 1. find sessions about a topic (FTS across every transcript)
sudo docker exec hermes-live sqlite3 $DB \
  "SELECT DISTINCT session_id FROM messages WHERE content LIKE '%green cat snake%';"

# 2. read one session's user+assistant turns (the human-facing story)
sudo docker exec hermes-live python3 - <<'PY'
import sqlite3
c=sqlite3.connect("/opt/data/state.db")
sid="20260708_125835_45e282"
for role,content in c.execute(
    "SELECT role,content FROM messages WHERE session_id=? AND role IN('user','assistant') "
    "AND content<>'' ORDER BY rowid", (sid,)):
    print(f"\n== {role.upper()} ==\n{content.strip()[:2000]}")
PY

# 3. the tool trace for a session (what it ran, in order) — from the policy log
sudo docker exec hermes-live sh -c \
  "grep '<tirith-session-uuid>' /opt/data/.local/share/tirith/log.jsonl | \
   python3 -c 'import sys,json;[print(json.loads(l)[\"timestamp\"][11:19], json.loads(l).get(\"command_redacted\",\"\")[:120]) for l in sys.stdin]'"

# 4. the SHAPE of a session (calls, tools, stalls) — from agent.log
sudo docker exec hermes-live sh -c \
  "grep '20260708_125835_45e282' /opt/data/logs/agent.log | grep -E 'turn_context|conversation_loop:'"
```
Note: `agent.log` uses the hermes session id (`YYYYMMDD_HHMMSS_xxxxxx`); the tirith policy log keys on its
own session UUID — match them by timestamp.

## The self-improvement loop (how a trace becomes a fix)
1. **Notice** a bad session (user pushback, a wrong answer, a stall) — or sweep FTS for risky patterns
   (a named species, a spatial "where", an empty result the agent glossed over).
2. **Reconstruct** it: recipe 2 for the answer text, recipe 3 for the tools it ran, recipe 4 for where it
   stalled or skipped tools. **Re-run the connector calls yourself** to see the real data (the log stores
   char-counts, not results — the transcript stores results, but live sources may have moved).
3. **Diagnose** the root cause (capability gap? routing? missing verification? bypassed the intended path?).
4. **Fix at the right layer** — usually the **PLAYBOOK** (a rule) or a **connector** (a guard), sometimes a
   **skill reference**. Record the limitation in `semantic_broker/LIMITATIONS.md` with the session id.
5. **Guard against negative learning:** the agent's own "update the skill library" turn also writes to
   `/opt/data/skills/…` — and it can persist *wrong* facts (it did: it mislabelled a snake and saved it).
   Treat auto-written skill files as **unverified** until reviewed; re-mine and correct them the same way.

## Caveats
- `state.db` is inside the container and owned by uid 10000 — read via `docker exec` (or `sudo` on the
  host mount), never assume host-shell access.
- Transcripts can be **compacted** (`compacted=1`) on long sessions — older turns may be summarised.
- Tool *results* in the transcript are a snapshot; live connectors (iNat/GBIF/EE) can return different data
  now — re-run to confirm before asserting a data fact.
- This is a read/introspection path. It is **not** a place to edit history; fixes land in the PLAYBOOK,
  connectors, or skills, not by rewriting `state.db`.
