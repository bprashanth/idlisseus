# EBTL data gaps → nice-to-have datasets (surface these, don't just refuse)

When a question hits genuine data scarcity at the **site** (the `need_more_data` / weak-gate
case), the valuable move is to name a **concrete, acquirable dataset** that would unlock it —
ideally one Varun's team can start collecting *today*. Refusing is not a win; "here's your best
bet now + here's what would sharpen it" is. These are the standing asks.

## 1. Higher-resolution hyperspectral (invasive / canopy chemistry)

- **Have:** EMIT (NASA/ISS) — 285 bands but **60 m** pixels, sparse/cloud-gapped. Good for a
  coarse "likely Lantana-*heavy*" signal (invasives form dense mono-stands), not crisp mapping.
- **Nice-to-have:** commercial hyperspectral at **~5 m — e.g. Pixxel (Firefly)** — enough to
  separate Lantana/Prosopis from native dry scrub at patch scale, map canopy water/senescence,
  and turn "probably invaded" into "these 2 ha are invaded."
- **The ask (data scarcity):** a tasked/archive **Pixxel (or similar ~5 m HS) scene over the
  site** would let us build a real invasive-cover map instead of a 60 m abundance hint.
- **POC path:** confirm on EMIT that invaded vs native separate spectrally at the site; use that
  to justify a higher-res tasking. (Method = transfer-by-similarity on the HS fingerprint;
  see `TRANSFER_ALGEBRA.md`.)

## 2. Bird data — hardware + landscape (eBird is the anchor, but it's effort-biased)

- **Have:** eBird hotspot **L36453021** = "Elephants by the Lake" (confirmed 12.7339,78.1834),
  **136 species** — the ABUNDANT site dataset. But **the "landscape field" is EMPTY** (confirmed:
  eBird obs carry species/location/date/effort only — NO habitat/land-cover). We recover habitat by
  annotating bird points with `landcover`. eBird is also effort-biased (accessible spots, presence-lean,
  no true absence). **Bridge already usable:** `ebird dispersers` → 11 Lantana-dispersing frugivores
  present → invasive-spread/connectivity signal despite 0 direct plant records.
- **Nice-to-have (two complementary, both startable now):**
  - **(a) Hardware bird detectors** — passive acoustic monitors (e.g. AudioMoth + BirdNET, or
    edge devices) deployed across the site's habitats give **continuous, unbiased, absence-aware**
    detections that eBird can't — especially cryptic/nocturnal species and dawn choruses.
  - **(b) Record the landscape the birds live in** — structured **eBird checklists + habitat
    notes** across the site's cover types (dense scrub, restored patches, cropland edge, lakeside),
    so occurrence can be tied to habitat and change tracked over restoration. This needs no new
    hardware — just directed effort on a platform they already have.
- **The ask (data scarcity):** either **deploy acoustic detectors** (best signal) and/or **run a
  structured eBird effort** stratified by habitat — both convert "we don't know site birds" into
  a growing, analyzable record.

## How Hermes should use this
When `predict.route` returns `need_more_data` (or a gate is weak) for an invasive/canopy or a
bird question at the site, **name the relevant ask above** as the constructive next step, alongside
the best gated estimate. This is encoded briefly in `connectors/PLAYBOOK.md` (the always-loaded
skill) so Hermes surfaces it.
