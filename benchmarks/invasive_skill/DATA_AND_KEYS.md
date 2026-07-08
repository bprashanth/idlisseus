# Data sources & API keys — invasive_skill

All keys live **outside the repo** in `~/.config/idlisseus/` (never commit them). The container reads EE
creds from `~/.hermes/`. Nothing here needs a cloud LLM key.

## Free, no key
| Source | What | Access |
|---|---|---|
| **Earth Engine** | Sentinel-2 (10 m, 5-day), WorldCover, **AlphaEarth** embeddings, WorldClim | creds already set: `~/.hermes/.config/earthengine/credentials`, project `plantwars`. Connectors self-init. Run connectors in the hermes container (venv `/opt/hermes/.venv`). |
| **GBIF** | species occurrence (research-grade) | `occurrence.py search --species "<name>" --bbox w,s,e,n` — no key. Note: research-grade only, so sparse for some species (0 Lantana in EBTL box). |
| **iNaturalist (direct)** | richer local observations incl. casual | `https://api.inaturalist.org/v1/observations?swlat=&swlng=&nelat=&nelng=` — no key. **EBTL bbox has 218 obs (97 plants)** vs ~0 via GBIF research-grade. **Add an iNat point-puller** — it's the best free local-points upgrade. |

## Keys (get + place)
| Key | File | Get it | Notes |
|---|---|---|---|
| **SkyFi** (high-res imagery) | `~/.config/idlisseus/skyfi.json` `{"api_key":"..."}` | app.skyfi.com/profile/api-keys-management | budget is a prepaid balance (was ₹5000; Phase A spent $44.88). **Top up in-app** for more scenes. Vantor (35 cm) needs the **Vantor EULA** accepted once (app.skyfi.com/accept-vantor-eula). Client: `skyfi.py` (budget-guarded). Cloudflare needs a browser UA (already handled). |
| **eBird** (birds) | `~/.hermes/secrets/ebird.json` or env | ebird.org/api/keygen | only for bird questions. |
| **Dryad** (papers) | `~/.config/idlisseus/dryad.json` | datadryad.org via ORCID | for `paper_data`; plot-level species lists = gold ground truth. |

## How to get MORE data (in priority order for this skill)
1. **iNaturalist direct pull** (free) — most local points for any species; wire a connector.
2. **Field GPS labels** — the gold standard. The `label_sheet.py` eyescan is the cheap proxy; a few
   real "Lantana / not-Lantana" GPS points calibrate everything.
3. **SkyFi high-res** — buy a **reference-region scene** where the species HAS GBIF records (Phase B, ~$48)
   to train+validate a transferable signature; or a 2nd EBTL date for high-res temporal. Needs balance top-up.
4. **Drone polygons (e.g. Gudalur)** — real labelled Lantana extents. Transfer caveats: different **sensor**
   (drone RGB vs WorldView-3 8-band → only RGB/texture transfer), **season** (lush vs dry), **ecoregion**
   (wet Nilgiris vs dry EBTL). Use as texture/color prior + validation, anchored on a few EBTL labels.
5. **paper_data** — dry-forest plot censuses (Bandipur/BRT) for co-occurrence + absence points.

## The Vantor scene we already have (EBTL)
`/home/beeps/skyfi/ebtl_superhigh.tif` — WorldView-3 **8-band** (coastal,blue,green,**yellow**,red,
**red-edge**,NIR1,NIR2), 35 cm, dry season 2026-04-02, ~1.87 km² over the site core. Yellow + red-edge are
Lantana-relevant. `ebtl_view.tif` = RGB view; `a1_data.json` = the free map; `a2_out/` = appearance-detector
outputs. Full provenance: `../semantic_broker/experiments/RESUME_VANTOR.md`.
