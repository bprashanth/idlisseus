# Elephants By The Lake — data-availability assessment

**For the EBTL / Rainmatter team.** For each question that matters to your
restoration, we searched real public data (no fabrication) and recorded: what we
found, whether it answers the question, and — where it doesn't — **what to collect**.
Searched 2026-07-03. Site: 70-acre dry-deciduous restoration near Veppanapalli,
Krishnagiri (ponds at ~12.735 N, 78.184 E; *South Deccan Plateau dry deciduous
forests* ecoregion).

Sources searched: GBIF (occurrence, inc. eBird), India Biodiversity Portal (via
GBIF), SoIB 2023 (State of India's Birds), Zenodo, CKAN gov catalogs, WII/WTI
elephant-corridor publications, and global Earth-Engine layers (MODIS, ESA
WorldCover, SRTM). "Analog" = same ecoregion outside the AOI (Bandipur–Mudumalai,
Sathyamangalam–BRT, Cauvery) used only when local data was thin, and always
labelled as such.

---

## ✅ Answerable now (real data found and run)

**1. Is the parcel actually recovering?** — **YES, measurably.**
MODIS NDVI 2019→2025 at the site rose **0.49 → 0.61 (+0.0137 / yr, "greening")** —
and *faster* than a nearby Melagiri forest reference point (+0.010/yr). Land cover
still classes as **Shrubland** (open/regenerating, canopy not yet closed), which is
exactly what an early-stage recovery looks like: greening up but not yet forest.
*Source: MODIS MOD13Q1 / ESA WorldCover. Caveat: 250 m pixels are coarse for 70
acres — for plot-level proof, re-run on Sentinel-2 (10 m) or your own drone NDVI.*

**2. Fire exposure** — **low.** ~1.5 fire-days within 5 km over 2020–2025 (the
forest reference had 0). Fire is not a major near-term threat here, but the
cropland edge carries the little there is. *Source: MODIS MOD14A1.*

**3. Which of the 67 birds you recorded matter nationally?** — **answered against
SoIB 2023** (Bird Count India; the same source your avifauna report cites).
63/67 matched. **Conservation-relevant species you host:**
- **Short-toed Snake Eagle** — *High* national priority, **currently declining**.
- **Indian Spotted Eagle** — *Moderate* priority, **IUCN Vulnerable**.
- **Common Woodshrike** — *Moderate*, **rapid long-term decline**.
- **Indian Roller**, **Oriental Magpie-Robin** — currently declining.
- **White-naped Woodpecker**, **White-bellied Drongo**, **Black-headed
  Cuckooshrike** — moderate priority / rapid recent decline.
- Plus 3 India-endemics (Grey Junglefowl, White-cheeked Barbet, Spot-breasted
  Fantail).
*This is a ready-made "why our birds matter" list. Source: SoIB 2023, Zenodo
10.5281/zenodo.11124590 (per-state CSV, fully queryable).*

**4. Regional baseline for flagship birds** — **rich** (eBird via GBIF): Short-toed
Snake-Eagle 89 records at the site box / 32,621 India; Grey Junglefowl 191 / 115k;
White-naped Woodpecker 18 / 21k. Enough to characterise habitat/where-recorded.

---

## 🟡 Partial — data exists, needs a small build or an analog

**5. Range & status of the native trees you plant** (Chloroxylon swietenia,
Diospyros montana, Wrightia tinctoria). GBIF has the **national** range (202 / 321 /
1221 India records) but the **local** signal is thin (1 / 0 / 4 at the site box).
→ Good enough to map each species' climate/habitat envelope and pick analog
seed-source regions; **not** enough for local provenance. Chloroxylon swietenia is
a known over-exploited timber (confirm IUCN via the IUCN API — needs a token).
*Recommendation: use analog dry-deciduous sites for range; collect local
phenology/seed-source GPS yourselves (see collect-list).*

**6. Rainfall / drought regime** (your establishment is rainfall-gated). Global
**CHIRPS** rainfall covers the site fully — we just haven't wired a connector yet.
*Build: a `rainfall` connector (one day's work).*

**7. Degradation / forest-change history** (the land was degraded before you). Global
**Hansen Global Forest Change** (annual loss/gain 2000–present) covers it. *Build: a
`forest_change` connector.*

**8. Pond permanence for the 42 odonate species.** Global **JRC Global Surface
Water** (monthly water 1984–present) can tell you how many months each pond holds
water and whether that's declining. *Build: a `water` connector.*

---

## 🔴 Data gap — collect it (we searched hard and it isn't openly queryable)

**9. Do elephants actually use the EBTL land, and where are the corridors?**
The **WII/WTI *Elephant Corridors of India 2023*** atlas (Project Elephant, MoEFCC)
*does* cover this landscape (Hosur / Dharmapuri / Sathyamangalam divisions) — but
only as a **published PDF atlas, not an open GIS layer** we can query, and GBIF
elephant records are sparse (1 at the site, 53 in the wider corridor). *→ Ask WII /
TN Forest Dept for the corridor shapefile; and log every elephant visit / deploy a
couple of camera traps at EBTL. This is the single highest-value thing to collect,
given the project's name.*

**10. Mammal presence/abundance** (sloth bear, etc.). GBIF is sparse everywhere for
these (bear 0 at site / 6 in corridor) — mammals need **camera traps**, and no
open camera-trap dataset exists for this block. *→ Collect: a small camera-trap grid.*

**11. Biodiversity change over time** (are birds/butterflies/herps increasing as
restoration proceeds?). Your **2024 faunal survey is the baseline** — but there is
no external time-series for this site, and unlike birds (SoIB) there is no national
trend dataset for butterflies/odonates/herps to borrow from. *→ Collect: repeat the
survey on the same transects annually (you're set up to; this is the highest-value
recurring dataset you can build).*

**12. Native-tree survival & growth in your restoration plots.** This is *your* data
(nursery, 15,000 saplings) and isn't public. *→ Structure it as a plot-level CSV
(plot id, species, planted date, survival, height) — then it becomes queryable and
we can correlate survival with NDVI/rainfall/soil automatically.*

---

## One-line summary for the team

You can already show, from public data, that **the land is greening faster than the
reference forest, at low fire risk, and hosts several nationally-declining and
IUCN-listed birds**. The biggest missing pieces are **elephant-movement / corridor
GIS** and **your own repeat biodiversity + sapling-survival records** — collect
those and almost every remaining question becomes answerable.
