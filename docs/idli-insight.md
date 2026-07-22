# Idli Insight: audited ecology answers in Odysseus

Last updated: 2026-07-23  
Baseline commit: `471f811b61ec81732714eeaa13484a0241188bc8`

## Purpose

Idli Insight is the provider-neutral chat surface for the Codex-native conservation workflow in
`totalrecall/ecology_memory`. It keeps the normal chat answer short while retaining a usable audit
of the admitted skills and data operations behind it.

The public model name is always `idli-insight`. The underlying model and routing details remain
server-side so changing a backend does not rename old conversations or expose infrastructure in
the transcript.

## Request path

```text
Odysseus browser
  -> /api/chat_stream
  -> Idli Insight model endpoint
  -> local Codex bridge on host port 7011
  -> bounded Codex session in the existing Hermes runtime
  -> allowlisted ecology skills and deterministic connectors
  -> answer + compact audit events
```

Odysseus supplies a stable chat session id. The bridge uses that id to resume one Codex thread,
which preserves conversational context without putting internal commands into the visible message.

The route also sends an `idlisseus_context` object containing the authenticated owner and session
id. Attachments are resolved through Odysseus's owner-aware upload resolver before their paths are
sent to the bridge. Missing or unauthorized uploads are omitted.

Relevant implementation:

- `chatbots/odysseus/routes/chat_routes.py`: attachment authorization and safe bridge-event filter.
- `chatbots/odysseus/src/llm_core.py`: bridge context, attachment manifest and event forwarding.
- `totalrecall/ecology_memory/integration/codex_native/server.py`: bounded runtime, skill gateway,
  audits and compatibility events.

## Live activity and the final answer

The browser recognizes three compatibility envelopes in streamed text:

- `idli-progress`: a safe activity label such as `Reading historical-fire-exposure`.
- `idli-skill`: one skill name, state, audit id and bounded result summary.
- `idli-insight`: the final compact list of invoked skills and the turn audit id.

These are HTML comments for compatibility with an older OpenAI-compatible event transport. They
are metadata, not answer prose. The stream parser consumes every complete envelope, including when
several envelopes arrive in one network chunk. The history parser removes them from already-saved
messages as well.

During a turn:

1. The wave spinner displays the current safe milestone or `Using <skill>`.
2. An open, vertically scrolling **Activity** disclosure records recent milestones and bounded
   skill summaries.
3. When answer text begins, temporary activity is removed from the prose area.
4. The final message receives a responsive **Why** disclosure listing each invoked skill and its
   bounded result summary.

Raw commands, filesystem paths, unrestricted connector rows, model routing and private model
reasoning are not rendered in the chat. They remain in the server audit.

The parser still recognizes the original `Codex CLI · native skill trace` and `Why · N skills
used` Markdown formats so historical chats become readable without rewriting the database.

Relevant implementation:

- `chatbots/odysseus/static/js/chat.js`: streaming envelope consumption and live Activity panel.
- `chatbots/odysseus/static/js/chatRenderer.js`: history cleanup, Why panel and model-request CTA.
- `chatbots/odysseus/static/style.css`: responsive audit, activity and action styles.
- `chatbots/odysseus/static/sw.js`: cache generation for shipping updated browser code.

## Audit ids

An audit id has the form:

```text
<chat-session-id>/<turn-number>
```

Clicking the audit id in the Why panel copies it. `/why` and `/audit` open and highlight the most
recent Why panel. The authenticated bridge endpoint can return the full, credential-redacted audit
for an exact turn:

```bash
curl http://127.0.0.1:7011/v1/audit/<session-id>/<turn> \
  -H "Authorization: Bearer $CODEX_NATIVE_API_TOKEN"
```

Omit the turn suffix to retrieve all turns for that bridge session.

## Missing-model requests

When an Idli Insight answer explicitly says that a model or predictor is missing, the message gains
a **Request this model from T4GC** button. This is deliberately user-triggered: detecting a gap does
not file a request.

Clicking the button sends a new chat turn that explicitly invokes the runtime-only
`request-model-from-t4gc` skill. The skill records a stable request id, requested capability,
region, reason, owner and audit id in:

```text
totalrecall/ecology_memory/integration/codex_native/runs/model_requests.jsonl
```

The file is created with mode `0600`. This operational skill is layered over the frozen benchmark
catalog and therefore does not mutate the historical 12-skill benchmark input.

## Cache affinity

For local OpenAI-compatible inference endpoints, Odysseus adds a stable `slot_id` derived from the
session and enables `cache_prompt`. This keeps follow-up turns on the same local prompt-cache slot
where supported. It is restricted to local endpoints and is not added to arbitrary remote APIs.

## Security boundary

- Only a small allowlist of bridge events reaches the browser.
- Skill names and summaries are inserted with DOM text nodes, not HTML.
- Upload paths are supplied only after an owner-aware authorization check.
- The bridge independently constrains uploaded files to its configured upload root.
- Audit output is credential-redacted before it is returned.
- The bridge token is an internal service credential, not an end-user authorization mechanism.

This remains a trusted-team proof of concept. Public multi-tenant deployment requires a dedicated
runner, egress policy and an independently authenticated Odysseus-to-bridge metadata channel.

## Tests

The baseline includes focused coverage for:

- owner-scoped attachment manifests and rejected uploads;
- filtering internal bridge events down to progress and skill events;
- stripping legacy and compatibility metadata from live and saved answers;
- safe DOM rendering of skill names and audit ids;
- coalesced progress/skill marker handling;
- responsive Activity and Why panels;
- explicit T4GC request action;
- local-only prompt-cache affinity; and
- generic Idli provider branding.

Run the focused tests inside the Odysseus environment:

```bash
cd chatbots/odysseus
python -m pytest -q \
  tests/test_idli_bridge_chat.py \
  tests/test_idli_insight_ui.py \
  tests/test_cache_affinity_local_only.py \
  tests/test_providers_mixtral_logo_js.py
```

## Known baseline limitation

The baseline `semantic-literature-discovery` ecology skill is not yet a general literature search.
It is bound to the fixed `EBTL Lantana literature` entity and searches the locally ingested semantic
card corpus with a Lantana-specific query. It does not perform live OpenAlex, Zenodo or Dryad
discovery for an arbitrary entity. Consequently, an Eucalyptus request can incorrectly exercise a
Lantana search. The next implementation phase must make discovery query-bound and preserve the
complete chain from hypothesis through admitted observations, gated estimate and mapped field-data
request.

