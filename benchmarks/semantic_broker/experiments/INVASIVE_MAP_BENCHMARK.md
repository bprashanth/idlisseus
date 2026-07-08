# Benchmark: picking the right map product for reliable invasive maps

**Question.** Under data scarcity (no in-AOI ground truth), *which map products + methods produce a
reliable invasive map, and when is paid high-res worth it?* We answer it as a real benchmark — with
hypotheses, metrics, decision rules, and a phased cost plan — so we neither over-trust free data nor
over-spend on imagery. Skill buckets per `../SKILL_ALGEBRA.md`. Forkable into the DSS repo (as the
method) and the UX pipeline (renders the outputs).

## The two approaches (two skill buckets, same target)

- **A1 — CHANGE (temporal), free.** Natives senesce in the dry season; invaders stay green. S2/AlphaEarth
  seasonal-change → invasive-likelihood. Coarse (10 m). *Already built* (`invasive.py`, `s2.anomaly`).
- **A2 — STATE (spatial), paid.** Detect Lantana by *appearance* — GLCM texture + OBIA segmentation + NIR
  spectral — in one high-res (Vantor 35 cm) scene. Fine (0.35 m).

Both use **TRANSFER** (signature learned off-site, since 0 GBIF Lantana fall in the AOI — nearest is
20.8 km). The benchmark's trick: **two independent buckets that agree = corroboration that stands in for
missing local ground truth.**

## The ground-truth problem and our four substitutes (ranked)

There is **no in-AOI field/GBIF label** yet. So "reliable" is established by, best→weakest:
1. **Transfer accuracy (real numbers).** In a reference region that DOES have GBIF Lantana, learn the A2
   signature at those points vs **matched negatives** (not-Lantana sampled from the *same* region's similar
   habitat — so the classifier learns Lantana, not habitat), and measure **held-out precision/recall/AUC**.
   This is the only source of a real accuracy figure.
2. **Cross-method concordance.** Do A1 (temporal, free) and A2 (spatial, paid) flag the *same* patches at
   EBTL? Independent methods agreeing ⇒ high confidence.
3. **Photo-interpretation.** At 35 cm, hand-label obvious Lantana thickets (mounded mid-green, lilac flower
   flush) as pseudo-labels.
4. **Field GPS (future gold).** A few "Lantana / not-Lantana" points from the site team calibrate everything.

## Hypotheses, metrics, decision rules

| # | Hypothesis | Metric | Decision |
|---|---|---|---|
| **H1** | S2 seasonal-change hotspots **predict where** high-res shows Lantana (⇒ "screen free, buy high-res only on hotspots") | rank-corr / top-decile IoU between A1 likelihood and A2 segments over EBTL | high ⇒ adopt **screen-then-buy** workflow (cheap, scalable). This is your **a/b/c**: a=concordant (S2 suffices), b=Vantor finds more/less (S2 biased), c=divergent (S2 unreliable) |
| **H2** | The A2 spatial method **works** (texture+NIR separates Lantana) | held-out **AUC/precision/recall** on reference-region GBIF vs matched negatives (substitute #1) | AUC ≥ 0.80 ⇒ trust A2's EBTL output; else A2 needs multi-date |
| **H3** | A1 ∩ A2 agreement = **high-confidence** Lantana without local field data | area & stability of the agreement mask; confidence tiers | produce a tiered map: "both agree" / "one only" / "neither" |

## Map products compared

| Product | Res | $ | Bucket / method | Role |
|---|---|---|---|---|
| S2 seasonal change | 10 m | free | CHANGE (stay-green) | coarse screen |
| AlphaEarth similarity | 10 m | free | STATE/CHANGE (embedding) | coarse analog |
| **Vantor 35 cm, 1 date** | 0.35 m | ~$45 | STATE (GLCM/OBIA/NIR) | fine confirm + segment |
| Vantor 35 cm, 2 dates | 0.35 m | ~$90 | CHANGE (fine temporal) | gold change (optional) |

## Phased plan + cost (do it well, no waste)

- **Phase A — EBTL scene ($44.88, committed).** VANTOR SUPER HIGH 35 cm, cloud-free 2026-04-02, ~1.87 km²
  over the restoration core + western hotspots (wpts 5–8). Runs: A2 segmentation (GLCM/OBIA/NIR) + **H1
  concordance** with the free A1 map + **H3** agreement map. Deliverable: is "screen-free-then-buy" valid,
  plus a fine segmentation over the plot.
- **Phase B — reference-region scene (~$48, after reviewing A).** VANTOR 35 cm over a GBIF-Lantana-rich
  cluster (20–40 km away). Runs: **H2** — learn the A2 signature at real GBIF points + matched negatives →
  **held-out accuracy**, then apply the trained segmenter to the Phase-A EBTL scene. The only real accuracy number.
- **Phase C — EBTL wet-season 2nd date (~$45, optional).** Only if A/B show high-res *temporal* beats
  spatial-alone. Direct 35 cm stay-green change.

**Cost:** committed **$45** (Phase A); full experiment **~$93** (A+B); with optional C **~$138**. Budget
loaded ₹5000 (~$60) → covers A + most of B; top up for B/C. Free: S2/AE/GBIF + all compute.
**Spend discipline:** A now → review H1/concordance → B for the real accuracy number → C only if needed.

## Outputs & where they fork

- **Method → DSS repo:** the phased protocol + `SKILL_ALGEBRA.md` buckets = the reusable "how to map an
  invasive under scarcity" recipe (generalises to any CHANGE/STATE target).
- **Data contract → UX pipeline:** each run emits `data.json` (grid likelihood + segments + agreement tiers
  + waypoints + method/confidence). The UX layer renders it (`render()` today) and can go wow-worthy
  independently — the model never has to change. Freeze this schema; that's the fork line.
- **Skill:** folds back into `invasive.py` as a `--product s2|vantor|both` option once validated.

## Status
- [x] A1 free map + waypoints (`invasive.py`)
- [ ] Phase A order + download (SUPER HIGH 35 cm)
- [ ] A2 segmentation (GLCM/OBIA/NIR) + H1 concordance + H3 agreement
- [ ] Phase B transfer-validation (H2 real accuracy)
- [ ] fold `--product` into the skill; freeze `data.json` schema for UX
