# Idli Insight model composition

Status: **implemented and running**

Last checked: 2026-07-24

This is the starting document for agents changing Idli Insight. It describes the live model
composition, why the models have different jobs, and which boundaries must remain visible and
auditable. It is an architecture description, not a proposal.

## The intent

Idli Insight separates conversational judgement from constrained scientific computation.

The outer model should be good at understanding a short or ambiguous question, holding a useful
conversation, discovering the resources available to an organisation, and deciding what to do
next. The inner model should express a sufficiently precise scientific question in a small,
validated language. Ordinary code should bind that expression to admitted data and execute it.

This gives each part a narrow responsibility:

| Part | Responsibility | Must not do |
|---|---|---|
| Codex CLI | Dialogue, clarification, resource discovery, connector and skill use, retries, and concise explanation | Turn model memory into local evidence or invent scientific results |
| Algebra 9B-004d | Compile one evidence-bound scientific question into the frozen Algebra IR | Choose sources, search connectors, converse with the user, or invent resource names |
| Trusted runtime | Validate IR, bind symbols to immutable result snapshots, run gates and operations, and record lineage | Make open-ended semantic decisions or silently repair rejected IR |
| Idlisseus/Odysseus | Session, streaming, visual artefacts, guided actions, compact provenance, and audit access | Expose private reasoning, credentials, raw commands, or infrastructure names as answer prose |

The composition is deliberately asymmetric. The 9B is not a second general assistant and is not a
post-hoc verifier. Codex does not ask it to approve prose. It is invoked only when the conversation
has reached an explicit state, relationship, trend, comparison, ranking, or transfer calculation
that can be grounded in admitted resources.

## The live request path

The public endpoint and model name remain stable while internal models can change:

```text
Browser at chat.idli.cc
  -> Idlisseus/Odysseus chat endpoint
  -> Idli Insight bridge on host port 7011
  -> Codex CLI executed inside the existing hermes-live container
  -> allowlisted skills and connectors
  -> optional Algebra 9B-004d compilation
  -> validated execution over immutable result snapshots
  -> streamed answer, guided actions, visual links, and audit events
```

The live browser-facing model name is `idli-insight`. Users should not need to know which
underlying model produced a particular conversational turn.

The bridge process itself runs on the host. For each chat session it prepares a private directory,
copies in the Codex CLI, the allowed inputs, and Codex authentication, then invokes the CLI with
`docker exec` inside the already-running `hermes-live` container. Codex runs there as uid/gid
65534. The Hermes image is therefore the execution boundary; the Hermes agent is not another
reasoning layer in this request path.

Idlisseus should be left in **Chat** mode for this endpoint. Codex CLI already supplies the agent
loop. Turning on Idlisseus Agent mode would add a redundant outer agent loop and is not the
architecture described or tested here.

## How a turn is handled

### 1. Codex owns the conversation

Codex receives the current user turn, bounded session context, the organisation's available
resource manifests, and progressive-disclosure skill descriptions. It may:

- answer a simple orientation question;
- ask one short question when a required entity, place, time, or comparison is ambiguous;
- search onboarded assets or admitted external sources;
- widen a search when local data are sparse;
- invoke a deterministic operation or visual renderer;
- offer a valid next action derived from the completed result; or
- explain a precise data or model gap.

General model knowledge can be used as labelled background or as an untrusted search seed. It is
not an admitted observation, source, or computed result.

### 2. Data is admitted before scientific compilation

Connector and skill results are stored as session-scoped, immutable snapshots. Each snapshot has a
stable result handle, source information, scope, and content hash. Later computation refers to
these handles instead of silently rerunning a connector.

This ordering matters:

```text
question -> discover/retrieve -> admitted result snapshot -> scientific compilation
```

It prevents the scientific compiler from naming a convenient dataset that was never actually
returned and prevents a later connector response from changing the meaning of an earlier answer.

### 3. Codex invokes the 9B only for a precise scientific question

When computation is warranted, Codex calls the `compile-scientific-algebra-9b` capability with:

- one short scientific question;
- the exact result handles that contain the evidence to use; and
- the code-owned manifest of available entities, regions, layers, gates, and operations.

The local 9B-004d receives the frozen grammar and these admitted symbols. It returns one Algebra
expression tree. It does not receive an open-ended skill catalogue and does not select connectors.

### 4. Code validates, binds, and executes

The runtime rejects unknown operations, invented resources, invalid types, and references that
cannot be bound to the supplied snapshots. It then binds valid leaves to the selected immutable
rows, evaluates gates, and executes the expression.

Codex cannot rewrite a rejected tree and present it as if it came from the 9B. It may clarify the
question, retrieve better evidence, or invoke the compiler again with new admitted inputs. This
supports backpedalling without weakening the audit boundary.

### 5. Idlisseus returns a concise result and a durable audit

The user sees:

- a short answer or clarification;
- visual or report links when an artefact was produced;
- guided next actions that are valid for the stored result;
- compact provenance classes; and
- a turn audit id.

The complete audit retains skill calls, bounded results, scientific question, exact IR, gates,
snapshot hashes, and execution lineage. Private reasoning, credentials, unrestricted connector
rows, raw commands, and internal model routing are not chat prose.

## Why the outer model remains important

Scientific questions rarely arrive fully specified. A user may name a place but omit a time
window, ask about a broad group rather than an entity, or ask for a conclusion when only nearby
data exist. A static pipeline would either reject too much or guess silently.

Codex supplies the flexible layer:

```text
ambiguous request
  -> resolve what the user means
  -> inspect what resources really exist
  -> ask or widen only when useful
  -> formulate the scientific question
  -> recover from a failed gate or rejected expression
  -> explain the result at the user's level
```

The trusted runtime remains intentionally thin. It enforces order, types, capability contracts,
lineage, and permissions; it should not grow into a second hard-coded domain planner.

## Why the inner model remains useful

A smaller specialised model makes the scientific decision boundary explicit. Instead of allowing
the conversational model to improvise a calculation, the 9B must express the calculation in a
frozen, inspectable form over resources that already exist.

This provides:

- deterministic validation before execution;
- stable benchmark targets independent of answer style;
- clear separation between retrieval and estimation;
- exact evidence-to-result lineage;
- a bounded surface for comparing future compilers; and
- the option to replace either model without rewriting the data plane.

The architecture does not depend on the 9B forever. The contract is “scientific compiler emits
validated IR”, not “this particular model is permanent”.

## Model and credential configuration

The bridge is OpenAI-compatible at its public boundary, but it launches the Codex CLI internally.
The live service currently resolves its unset model override to `gpt-5.4` and uses
ChatGPT-authenticated Codex credentials. The bridge supplies the selected model name and reasoning
level to `codex exec`.

Codex CLI also supports API-key-backed and custom compatible providers. Deployment launch profiles
can therefore change the Codex base model without changing the browser model name, chat protocol,
skill gateway, or audit format. Provider credentials must be injected through the service or
Codex authentication/configuration boundary; they must never be copied into prompts, organisation
data, reports, audits, or repository files.

The 9B runs behind its own local OpenAI-compatible endpoint and model id. That endpoint is called
only by the scientific compilation capability. Changing the Codex base model does not implicitly
change the 9B, and changing the 9B does not turn it into the outer dialogue model.

## Session and isolation model

One Idlisseus chat session maps to one resumable Codex thread. Separate browser chats do not share
a Codex thread. Within a chat, the bridge preserves:

- the Codex thread id;
- turn number and audit;
- admitted result handles;
- pending guided actions; and
- a bounded investigation history.

The container runner receives a private home, input, work, and output tree for that session.
Attachments are copied only after Idlisseus has resolved them for the authenticated owner and the
bridge has confirmed they are under the configured upload root.

The current deployment is suitable for a trusted team proof of concept. It is not yet a hardened
public multi-tenant execution service: the host bridge can issue narrowly constructed
`docker exec` calls, the runner has network access, and the internal bearer token is a service
credential rather than end-user authorization.

## Failure handling

The system should fail at the boundary that actually failed:

| Failure | Correct behaviour |
|---|---|
| Ambiguous user intent | Ask one short clarification |
| No local result | Say that a non-match is not absence; offer a bounded wider search |
| Connector unavailable | Identify the unavailable source and preserve other valid results |
| No transferable data | Show where admitted data do exist before asking for new collection |
| Missing required value | Surface the typed hole to Codex for a short question |
| Scientific IR rejected | Report the rejection in audit; clarify, retrieve, or recompile |
| Gate fails | Keep observed-data visuals useful and explain why estimation did not run |
| Required model absent | Return a structured model/data request; never fabricate the output |

Guided actions must be capability-derived. A DOI, filename, or result label alone is not proof that
the next operation can consume it. Results should explicitly declare capabilities such as
`inspectable`, `mappable`, or `eligible_for_transfer`, and the UI should offer only actions whose
input contracts can be satisfied.

## Invariants for future agents

1. Keep `idli-insight` as the generic public name; backend names belong in logs and operator docs.
2. Keep dialogue/resource discovery outside the scientific compiler.
3. Retrieve and store evidence before asking the compiler to use it.
4. Bind computation to immutable result handles, not fresh hidden connector calls.
5. Let code validate and execute IR; do not let Codex silently author or repair it.
6. Keep the runtime thin: enforce contracts, do not hard-code conversational scripts.
7. Preserve useful observed-data output even when a later model or gate fails.
8. Do not expose an action unless the stored result declares the capability it needs.
9. Keep model background, local assets, public data, proxies, modelled results, designed outputs,
   and gaps distinguishable in both UI and audit.
10. Treat credentials and model routing as deployment configuration, never user-visible evidence.

## Where to look next

- [`../README.md`](../README.md) — repository entry point and live service summary.
- [`odysseus.md`](odysseus.md) — Idlisseus/Odysseus application path.
- [`agents.md`](agents.md) — agent runtime and container operations.
- [`hermes-token-proxy.md`](hermes-token-proxy.md) — token-proxy details for other Hermes uses.
- `totalrecall/.../integration/codex_native/README.md` — implementation-specific bridge operations,
  tests, and audit commands in the companion repository.
