# Idli Insight: audited ecology answers in Odysseus

Last updated: 2026-07-24
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

The bridge strips Idlisseus's injected date/time transport block before ecology routing and local
semantic queries. This prevents calendar words from selecting an unrelated evidence partition;
the raw request remains available in the server audit.

Relevant implementation:

- `chatbots/odysseus/routes/chat_routes.py`: attachment authorization and safe bridge-event filter.
- `chatbots/odysseus/src/llm_core.py`: bridge context, attachment manifest and event forwarding.
- `totalrecall/ecology_memory/integration/codex_native/server.py`: bounded runtime, skill gateway,
  audits and compatibility events.

## Live activity and the final answer

The browser recognizes five compatibility envelopes in streamed text:

- `idli-progress`: a safe activity label such as `Reading historical-fire-exposure`.
- `idli-skill`: one skill name, state, audit id and bounded result summary.
- `idli-insight`: the final compact list of invoked skills and the turn audit id.
- `idli-actions`: a validated question and up to three guided next-step labels.
- `idli-evidence`: controller-derived evidence classes for the completed answer.

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
5. A compact badge row identifies **Local asset**, **Public data**, **Proxy**, **Modelled**,
   **Designed**, **Data gap**, and **Model background**. Icons, text and colour are all used so the
   distinction does not depend on colour alone.

The dialogue model cannot award itself a `Modelled` badge. The bridge emits that class only after a
validated `ESTIMATE` answers or a map contains an admitted modelled surface. A failed gate that
produces balanced collection points is labelled `Designed`.

Broad site orientation, local-registry lookup, accumulated-dashboard publication, historical-fire
exposure and vegetation-greenness trend are deterministic capability routes. The runtime starts
these immediately and streams their skill state before Codex writes the short explanation. Fire
and greenness remain labelled historical/remote-sensing proxies with their geometry and time
limits. This reduces time to first useful result without letting the dialogue model choose an
unrelated local asset or substitute source.

Raw commands, filesystem paths, unrestricted connector rows, model routing and private model
reasoning are not rendered in the chat. They remain in the server audit.

The parser still recognizes the original `Codex CLI · native skill trace` and `Why · N skills
used` Markdown formats so historical chats become readable without rewriting the database.

## Guided investigations

Idli Insight defaults to one evidence-bearing stage per turn unless the user explicitly requests
the complete workflow. The Codex model selects and explains the current scientific operation; a
deterministic capability graph derives only the operations that are valid after its audited skill
result.

A modelled-map choice is an ordered exception: the trusted runtime requires donor occurrence retrieval,
then Algebra 9B compilation, then the map renderer. Calls made out of order are rejected.
For an explicit free-text map request, the controller also checks completion: if Codex finishes a
valid estimate but omits the renderer call, it renders the map from the latest admitted taxon and
adds the link in the same turn.

For example:

```text
local evidence
  -> bounded wider admitted occurrences
  -> immutable observed-data coverage map OR environmental transfer test
  -> modelled field map or failed-gate confirmation design
```

The next operations appear through Odysseus's existing durable `ask_user` choice card. A click
sends the short visible label as the user's next turn. The bridge resolves that exact label against
the pending session state, binds the stored entity/region arguments, and limits the selected turn
to the authorized skill set. An unrelated typed message invalidates the old pending actions.

This is a capability graph, not a species script. Species, AOI, donor region and result handles are
carried from audited skill inputs and outputs. An empty exact-site occurrence retrieval can offer a
bounded wider search, but not transfer. Once coordinates return, the exact result handles can be
mapped even if every later gate fails. Discovery results are offered for inspection only when their returned title
matches a focal query term; a repository search hit alone is not evidence.

The raw-map branch calls `build-ecology-field-map` with `map_mode: observed`. It does not invoke an
estimator or create synthetic field points. The map exports every returned observation with stable
`OBS-...` ids; its potentially long record table is collapsed by default. `map_mode: modelled`
remains a separate user-selected operation. If the intended occurrence source fails and no
source-identified cache is admitted, the map does not switch connectors: it returns stable
`FIELD-...` points labelled `Designed`.

The preferred wider-data visual is `map-evidence-coverage`. It reads one or more immutable
current-session result handles, accepts several taxa/sources, outlines and marks the target AOI,
and never reruns a connector or estimator. Its colour-coded points remain observations; stable
`OBS-*` ids are retained in the table, CSV and GeoJSON.

Pending action state and a bounded investigation history are stored with the resumable bridge
session. The scientific Algebra remains unchanged: typed holes still cover missing values, while
guided actions cover user decisions to expand scope.

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
totalrecall/ecology_memory/integration/codex_native/runs/service/sessions/model_requests.jsonl
```

The file is created with mode `0600`. This operational skill is layered over the frozen benchmark
catalog and therefore does not mutate the historical 12-skill benchmark input.

The button asks the agent to structure the request with the missing response variable, candidate
predictors, labels or ground truth, spatial extent and a measurable validation target. Unknowns are
recorded as unknown rather than silently filled from model memory.

## Query-bound evidence and field maps

The generic evidence/runtime layer extends the frozen benchmark catalogue, alongside the separate
T4GC request skill described above:

- `discover-ecology-evidence` passes the user's actual query to the admitted local semantic,
  OpenAlex, Zenodo and Dryad connectors. Model knowledge may supply a labelled query seed, but a
  candidate is not actionable until one of these sources returns it.
- `inspect-evidence-dataset` opens a Zenodo/Dryad result by its discovery `result_id` and DOI and
  returns its real files, headers, sample rows and codebook text. Protocols and datasheets must cite
  this material and label adaptations. DOI matching accepts repository-prefixed (`doi:`), bare and
  `https://doi.org/` forms; an exact Dryad DOI lookup gets one bounded same-query retry when its
  file-list request transiently returns no rows.
- `relate-taxon-occurrences` retrieves two named taxa in one admitted region, calculates pairs at
  a declared distance, and keeps both input denominators in the audit. The short label
  `donor belt` resolves to the declared dry-Deccan donor belt. Its answer must state that proximity
  does not prove interaction, shared habitat or simultaneous presence.
- `build-source-backed-field-protocol` turns an inspected dataset into a side-panel protocol reader
  and blank CSV datasheet. Returned source columns stay separate from programme-added point, effort,
  detection and notes fields. When a codebook declares several tables, the caller selects one
  declared source filename rather than merging unrelated columns.
- `build-ecology-field-map` retrieves and gates every taxon independently, then creates a
  self-contained HTML map plus matching CSV and GeoJSON field points. A failed fine-scale model
  produces a labelled spatial sampling design; it does not draw invented overlap. Its separate
  observations-only mode maps returned records without running a gate or estimator.
- `map-evidence-coverage` renders georeferenced rows from current-session result handles exactly as
  returned, together with the target AOI. It is the default “where does data exist?” map and
  remains useful after a failed transfer.
- `discover-biotic-interactions` queries source-linked GloBI interaction rows for a named source
  taxon and optional target/relation. It supplies evidence-derived candidates and retained source
  identifiers; it never asserts that the indexed interaction occurs at the site.
- `publish-evidence-dashboard` accepts only current-session result handles. The runtime derives
  its cards, row-count visuals, map links and gap list. It cannot accept model-authored metrics,
  claims or HTML.

Discovery and inspection results receive session-scoped handles. The map skill records the handles,
gate results, point ids and document id in the normal audit. Map links use the form:

```text
[Open field map](#map-<document-id>)
```

The `#map-` link opens Odysseus's existing HTML document side panel. HTML documents automatically
enter the sandboxed preview, so the user sees the responsive map instead of source code. The map
has toggleable observed/modelled layers, numbered collection points, interpretation limits and
download buttons for its matching GeoJSON and CSV field sheet.

Map/document anchors are captured before generic hash navigation, and `map-` hashes are excluded
from chat-session routing. Read-only HTML artefacts preserve the active **Chat** mode when their
document pane mounts; opening a map must not reset the conversation or switch it to Agent mode.

The evidence contract is strict:

```text
model hypothesis -> admitted query result -> retrieved data -> independent gates
                 -> estimate or precise DataRequest -> answer + audit -> field map
```

For scientific execution, outer Codex supplies one short question and the exact evidence-result
handles. Algebra 9B emits only frozen IR. Trusted code validates its symbols, binds an `ESTIMATE`
donor `SELECT` to the exact extent of the explicitly selected occurrence snapshot, and executes
from those immutable rows without rerunning the connector. The extent binding and snapshot hash
remain in the audit. Codex—not this runtime—chooses whether to widen, retry, map or ask the user.
The legacy direct transfer binding remains only for frozen benchmark reproducibility and is
rejected in interactive chat.

For relation questions, “admitted query result” means one returned source that directly connects
the candidate, focal entity and requested relation. A general paper naming the candidate may seed a
new `candidate + focal entity + relation` search, but it is not enough to send that candidate into
occurrence or estimation. If only one admitted named taxon remains when the user requests a map,
the map may show a one-taxon balanced collection design and must say it is not two-taxon overlap.

Spatial overlap remains a confirmation hypothesis. It is not evidence of dispersal, avoidance,
shared habitat or simultaneous presence.

The bridge currently reports 24 visible skills: the frozen 12 plus 12 operational skills. The
current multi-turn operational bank is in Totalrecall at
`ecology_memory/narrative/benchmarks/site-ecology-dialogue/`. It scores the Codex-outer +
Algebra-9B compiler architecture directly; the 9B is not a post-hoc verifier.

Local evidence has routing priority over broad discovery. A local-site question first invokes
`local-site-evidence-search` with the focal entity or topic. The skill is taxon-neutral: an ecology
organisation supplies a local evidence adapter and site aliases, rather than adding one skill per
species. The EBTL adapter currently covers local survey, bird, snake, elephant-passage, nursery,
soil and evidence-summary categories. Returned limitations remain intact, and a registry non-match
is not absence. Literature discovery is used when the user asks for wider papers/datasets or after
the local result is made clear.

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
- persisted guided choices, safe action forwarding and single-option cards;
- responsive Activity and Why panels;
- explicit T4GC request action;
- query-bound discovery with session-scoped result handles;
- generic two-taxon proximity with a declared threshold and both denominators;
- matching map, GeoJSON and CSV point ids;
- observations-only maps that never invoke an estimate;
- `#map-` side-panel routing through the existing sandboxed HTML preview;
- map hash isolation and Chat-mode preservation;
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

## Frozen baseline comparison

The frozen `semantic-literature-discovery` benchmark skill remains bound to `EBTL Lantana
literature`. It is retained unchanged so historical runs stay reproducible. New conversations should
use `discover-ecology-evidence` for arbitrary questions. Keeping the operational repair outside the
frozen twelve-skill catalogue makes the old Eucalyptus-to-Lantana failure directly testable without
preserving it as current behaviour.
