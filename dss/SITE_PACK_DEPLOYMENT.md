# Generic site-pack deployment through Idlisseus

Status: proof-of-concept deployment contract.

Last checked: 2026-07-24

This document applies to any place-based benchmark or programme, including livelihoods, health,
education, conservation, infrastructure, and public-service delivery. A “site” can be a parcel,
village, district, facility catchment, programme area, comparison region, or other declared
analysis scope.

Pack authoring for a new sector (exact manifest schemas, adapter kinds, build/verify steps) is
documented benchmark-side in `totalrecall/dss/SITE_PACK_AUTHORING.md`, with
`totalrecall/dss/sites/valparai_livelihoods/` as the synthetic reference pack.

Idlisseus owns conversation, presentation, endpoint registration, sessions, and audit UX. It does
not own benchmark source data. Each benchmark repository owns its site packs, ingestion adapters,
indexes, connectors, skills, model inputs, and derived evidence.

## Boundary

```text
benchmark repository
  site pack + source registry + raw versions
  ingestion and index builder
  benchmark-specific connectors and skills
  bridge launcher
             |
             | OpenAI-compatible stream + bounded result contracts
             v
Idlisseus
  endpoint registry + model selector
  chat session and streaming
  activity, provenance and audit presentation
  maps, charts, dashboards and drill-down viewers
```

Source files remain in the benchmark repository or its configured data store. A bridge may build
a disposable serving index under its own runtime state directory. Idlisseus should receive result
handles, bounded rows, visual contracts, artefact URLs, provenance, and capability metadata—not a
second copy of the source pack.

## Minimum pack contract

A pack should contain:

```text
sites/<site-id>/
├── site.json          stable id, label, aliases, organisation, scope and geometry roles
├── sources.json       source versions, rights, hashes, capabilities and schema adapters
├── questions.json     optional representative question and visual probes
└── raw/               immutable attributed source versions or resolvable source manifests
```

The pack may additionally declare:

- named places and boundaries;
- entities, aliases and hierarchies;
- event, exposure, effort, measurement and intervention adapters;
- document and semantic indexes;
- feature cubes;
- admitted models and validation gates;
- access and coordinate-sensitivity policy; and
- visual views that can be materialised.

The serving build should produce versioned or reproducible outputs such as:

```text
site_index.sqlite      canonical facts and fast filtered queries
visual_bundle.json     declared visual-ready views and availability
build_report.json      source counts, integrity checks and build identity
tiles/                 optional map or aggregate tiles
artifacts/             optional generated reports, maps and dashboards
```

SQLite is sufficient for the current proof of concept. The contract does not require a particular
database in production.

## POC selection policy: one site per bridge process

Do not switch data scopes merely because a place name appears in a prompt. Run one bridge process
per benchmark/site combination. Give each process its own:

- pack path;
- port;
- state, sessions and cache directory;
- public model id;
- Idlisseus endpoint name; and
- benchmark connector/skill configuration.

One Idlisseus installation can register many such endpoints. Users select the appropriate
endpoint when starting a chat. This is simpler and safer than deploying one UI per site, and it
prevents one conversation from silently crossing data boundaries.

Example endpoint inventory:

| Benchmark | Site | Port | Public model | Idlisseus label |
|---|---|---:|---|---|
| livelihoods | programme-a | 7021 | `insight-livelihoods-programme-a` | Insight — Programme A |
| livelihoods | programme-b | 7022 | `insight-livelihoods-programme-b` | Insight — Programme B |
| health | district-a | 7031 | `insight-health-district-a` | Insight — District A |

Port and name allocation should live in a versioned deployment registry outside Idlisseus source
code. Never reuse one running state directory for two packs.

## Compatible launcher interface

Each benchmark integration should expose a small launcher with this interface:

```text
setup_idlisseus.py start
setup_idlisseus.py status
setup_idlisseus.py stop

--idlisseus <Idlisseus application directory>
--site-pack <benchmark-owned pack directory>
--state <site-specific runtime state>
--port <unique host port>
--public-model <stable browser model id>
--endpoint-name <human-readable Idlisseus label>
```

On `start`, the launcher should:

1. validate `site.json` and `sources.json`;
2. build or verify the derived serving index;
3. pin the pack path, aliases, digest and connector configuration in the bridge environment;
4. start the bridge;
5. wait for its health endpoint; and
6. register or update the endpoint in the Idlisseus database.

On `stop`, it should terminate only the process identified by that state directory. Stopping a
bridge does not delete its source pack, derived index, audit, or Idlisseus endpoint registration.

## Start the Idlisseus UI

From the Idlisseus repository:

```bash
cd chatbots/odysseus
docker compose up -d
docker compose ps
```

Follow application logs with:

```bash
cd chatbots/odysseus
docker compose logs -f odysseus
```

Rebuild the UI after source or static-asset changes:

```bash
cd chatbots/odysseus
docker compose build odysseus
docker compose up -d --force-recreate odysseus
```

Restarting the UI does not require rebuilding every site pack. Restarting a site bridge does not
require restarting the UI.

## Start a benchmark/site endpoint

Set deployment-specific paths and values:

```bash
IDLISSEUS_REPO=/absolute/path/to/idlisseus
BENCHMARK_REPO=/absolute/path/to/benchmark-repository
SITE_LAUNCHER="$BENCHMARK_REPO/path/to/setup_idlisseus.py"
SITE_PACK="$BENCHMARK_REPO/dss/sites/programme-a"
SITE_STATE="$BENCHMARK_REPO/runs/insight-programme-a"
SITE_PORT=7021
SITE_MODEL=insight-livelihoods-programme-a
SITE_LABEL="Insight — Programme A"
```

Then start and register it:

```bash
python3 "$SITE_LAUNCHER" start \
  --idlisseus "$IDLISSEUS_REPO/chatbots/odysseus" \
  --site-pack "$SITE_PACK" \
  --state "$SITE_STATE" \
  --port "$SITE_PORT" \
  --public-model "$SITE_MODEL" \
  --endpoint-name "$SITE_LABEL"
```

The launcher is benchmark-owned because it must inject that benchmark's connector and skill
configuration. Idlisseus only requires the resulting OpenAI-compatible endpoint and safe stream
metadata.

## Status, logs, stop, and restart

Check process state:

```bash
python3 "$SITE_LAUNCHER" status \
  --state "$SITE_STATE" \
  --port "$SITE_PORT"

curl -fsS "http://127.0.0.1:$SITE_PORT/health"
```

Inspect bridge logs:

```bash
tail -f "$SITE_STATE/server.stdout.log"
tail -f "$SITE_STATE/server.stderr.log"
```

Stop only this site:

```bash
python3 "$SITE_LAUNCHER" stop --state "$SITE_STATE"
```

Restart after a pack, adapter, connector, skill, or bridge change:

```bash
python3 "$SITE_LAUNCHER" stop --state "$SITE_STATE"

python3 "$SITE_LAUNCHER" start \
  --idlisseus "$IDLISSEUS_REPO/chatbots/odysseus" \
  --site-pack "$SITE_PACK" \
  --state "$SITE_STATE" \
  --port "$SITE_PORT" \
  --public-model "$SITE_MODEL" \
  --endpoint-name "$SITE_LABEL"
```

Use the Idlisseus model selector to begin a new chat on the restarted endpoint. Existing chat
history remains in Idlisseus; resumable backend state depends on the bridge retaining its
site-specific state directory.

## Updating a pack

Treat a data update as a versioned build:

1. add a new immutable source version or organisation-provided asset;
2. update the source registry, schema adapter, rights and content hash;
3. rebuild the serving index;
4. run integrity, query, visual-contract and leakage tests;
5. record the pack/build digest;
6. restart only that site's bridge; and
7. verify site overview, one entity/metric query, one visual and the audit trail.

Never edit raw source files in place. Never let a failed source or schema change silently select a
different source.

## What Idlisseus may assume

The UI may assume only the cross-benchmark result contract:

- stable session, turn, audit and result ids;
- evidence class such as observed, reported, proxy, modelled, designed, or gap;
- source and scope labels;
- capability declarations such as inspectable, mappable, comparable, or eligible for transfer;
- bounded rows or aggregate references;
- visual specifications or safe artefact URLs;
- limitations and failed gates; and
- valid next actions derived from result capabilities.

It must not hard-code benchmark entity names, source names, units, map layers, question scripts, or
model operations.

## What the benchmark integration must guarantee

The benchmark side must:

- resolve site and organisation aliases from the pinned pack;
- parameterise connectors and skills with explicit site/result handles;
- keep source retrieval separate from computation;
- bind calculations to immutable admitted snapshots;
- preserve source rows and denominators;
- label model outputs and failed gates;
- return an observed-data visual when later modelling is unavailable;
- prevent a site-bound operation from borrowing another site's defaults; and
- redact credentials, unrestricted records, raw commands and private reasoning.

## Future single-endpoint routing

A later design may expose one public endpoint across many packs, but prompt mentions must not be
the tenancy mechanism. A safe implementation should:

1. resolve organisation and site from an authenticated registry when a session starts;
2. ask when aliases are ambiguous;
3. pin `organisation_id`, `site_id`, pack digest and access policy in session state;
4. pass explicit site/result handles to every connector, skill, model and renderer;
5. reject silent scope changes during a session;
6. partition caches and artifacts by organisation/site/digest; and
7. make deliberate cross-site comparisons a typed operation over authorised inputs.

Language reasoning may interpret the question. The registry and pinned session decide which data
the reasoning is allowed to inspect.

## Validation checklist

- The Idlisseus UI and every selected bridge report healthy.
- Endpoint model ids are unique and appear in the model selector.
- “Tell me about this site” resolves the pinned pack.
- An alias query returns rows from the expected source registry.
- A registry miss is described as a non-match, not absence.
- A visual opens and drills down to source rows or a disclosed boundary.
- Audit ids resolve to the correct site-specific runtime.
- A legacy or foreign-site capability is refused.
- Restart rebuilds the derived index without modifying raw data.
- Two simultaneously running site endpoints cannot see each other's rows or state.
