# Valparai visual site pack

Status: first feasibility implementation of `visual-site-pack/0.1`.

This site pack consolidates the source files, AOI roles, aliases, source adapters and question
probes used to test the future visual-first data design. It is not yet connected to live chat.

## Contents

```text
site.json       AOI roles, aliases and named points
sources.json    source registry, rights and schema-driven adapters
questions.json  representative question-to-first-visual probes
raw/            immutable attributed source subsets used by the prototype
```

The target geometry is the published Valparai Plateau study envelope, not a parcel or ownership
boundary. Organisation-supplied KML/GeoJSON should replace or supplement it during onboarding.

## Build and test

From the Idlisseus repository root:

```bash
python3 dss/visual_index/build.py \
  --site-pack dss/sites/valparai \
  --output /tmp/valparai-visual-index

python3 -m unittest dss.visual_index.tests.test_build -v
```

The current build indexes:

- 13,592 source-linked events;
- 13,577 georeferenced events;
- 543 resolved or retained broad entities and 1,039 aliases;
- 29 named/source locations;
- 229 explicit effort rows;
- 580 monthly metric values; and
- 284 spatial cells.

Eight of the ten probed visual contracts are immediately renderable. Transfer is partial because
the pack does not yet include a versioned feature cube and gate result. Expected-value collection
mapping is blocked because there is no versioned uncertainty surface or action-cost layer.

## Important data findings

- The three presence datasets use scientific names, underscored common names and spaced common
  names. Explicit crosswalks and aliases are required; simple string grouping splits the same
  entity.
- Several source rows use broad labels at different hierarchy levels. The index retains them
  rather than pretending every row is at the same rank.
- Presence records and explicit survey effort come from different planes. The builder never
  manufactures effort from the number of presence rows.
- One plot dataset stores entities and coordinates in separate files joined by point id. All 3,684
  plot rows join to their source locations.
- Some records lie outside the target study envelope. They remain visible as context/donor data
  rather than being discarded or described as target observations.
- The available long metric series is suitable for time visuals. Event counts by year are coverage
  visuals, not population trends.
- 4,552 georeferenced event rows are outside the target envelope; 9,025 are inside it.
- Twenty-five opportunistic effort rows have no matching route geometry. They remain explicit
  effort records but cannot appear in a cell-level effort map.
- Fifteen event rows have no usable coordinates. They remain queryable through source and time
  fields instead of being dropped.
- Upstream natural keys are reused in 14 rows. Stable event ids therefore include the immutable
  source-row locator as well as the source's identifier.
- The 2024 source metadata describes a name crosswalk that is absent from the local source subset.
  Those common names resolve only when an earlier admitted crosswalk matches; other labels remain
  unresolved rather than being guessed.

See [`raw/README.md`](raw/README.md) for source attribution and licence details.
