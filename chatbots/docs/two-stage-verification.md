# Two-Stage Citation Verification (Research Mode)

**Status:** design doc only — not built.

## Problem

Level 1 (current) trusts the model to accurately cite sources. The model can:
- Cite a source that doesn't support the claim
- Hallucinate a claim and attach a real-looking citation
- Cite source [3] when [1] was the actual source

We want the system to catch this automatically, not rely on the user reading the sources.

## Proposed design

**Research mode** (opt-in toggle in the chat toolbar):

### Pass 1 — Draft with markers
System prompt instructs the model to draft a response where every factual claim
carries `[UNVERIFIED: <short-query>]` instead of a citation. The `<short-query>` is
the specific search that would verify that claim.

Example output:
> The 2024 global average temperature was 1.54°C above pre-industrial baseline
> `[UNVERIFIED: global average temperature 2024 anomaly]`

### Pass 2 — Bounded verification
Agent extracts all UNVERIFIED markers, deduplicated. For each:
- Runs a targeted `web_search(<short-query>)`
- Checks: does any returned source support the claim?
- If yes: replaces `[UNVERIFIED: ...]` with `[N]` (numbered citation, source added to panel)
- If no: replaces `[UNVERIFIED: ...]` with `[COULD NOT VERIFY]`

### Constraints
- Max 10 verification searches per response (prevents spiral)
- Timeout: 30s total for all verifications (parallel if possible)
- Falls back gracefully if search fails: keeps `[COULD NOT VERIFY]`

## Why not build this now

Current blocker: `trigger_research` tool already exists but is model-directed, not
system-directed. Implementing two-pass requires:
1. Parsing the draft for UNVERIFIED markers (deterministic, easy)
2. Running the verifications as server-side parallel searches (medium complexity)
3. Rewriting the response with confirmed citations (medium complexity)
4. UI toggle + progress indicator so users know they're in Research mode

Estimated 2–3 days of work. Not started because:
- Prompt-only Level 1 is working for current use cases
- Need to validate that the draft format is stable enough to parse reliably
- Level 3 adds latency (pass 2 adds 10–30s); user needs to opt in consciously

## Alternative approaches considered

**Agent self-verification loop** — agent searches and then fact-checks its own output.
Rejected: no stopping condition, tends to spiral, and the model is not reliable as its own judge.

**Post-hoc retrieval check** — after response, search for each sentence, compute semantic similarity.
Rejected: expensive, noisy, hard to present to user in a useful way.

**Two-LLM judge** — draft model + judge model reviewing citations.
Rejected: we have one model at a time; would need 2B sidekick as the judge, but 2B is too small for judgment.
