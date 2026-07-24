# Recipe: "where is X / where can I find X" — a MAP, for ANY taxon (L2)

**A spatial "where" question is a MAP question, never a single GPS point.** One occurrence dot is "where
someone once saw it", not "where you can find it". Give a modelled likelihood/suitability map + the
confirmed points + the honest caveat.

### 0. Resolve the name (always)
`points.py resolve --species "<name>"` — a common name can be the wrong species. Use the scientific name.

### A. Plants / invasives → the one-command funnel
```
python /opt/data/connectors/invasive.py map --species "<Scientific name>"
```
→ a field-navigable HTML map + GPS waypoints in `/opt/data/work/invasive/<species>/`. Under the hood
(all free): EE RandomForest on that species' recent GBIF/iNat records vs background over a 6-band S2
stack + multi-year stay-green phenology (evergreen invaders stay green in the dry season). Building
blocks if needed piecemeal: `s2.py anomaly_grid`, `embedding.py similarity`, `points.py get` (validate).

### B. Any species incl. FAUNA (snake, spider, bird) → habitat-suitability transfer
A snake/spider rarely has enough local points to map directly. Do the transfer:
1. `points.py get --species "<name>" --bbox <wider analog belt>` → donor occurrence points.
2. `predict.py route --points <donor.csv> --bbox <site w,s,e,n> --question presence` → runs the gate +
   every valid method (RF on satellite analog / climate SDM) and returns a **situation**
   (answerable / need_more_data / need_better_models) + a suitability surface.
3. Annotate with the species' known habitat drivers (`terrain` elevation/rock for saxicolous/cave taxa,
   `landcover`/`s2` canopy for arboreal taxa, `water` for riparian) to sharpen "where".
Report it as **modelled suitability**, show the confirmed points separately, and say "walk these to confirm".

### C. Offer the ground-truth lens (any transfer onto a map)
`groundtruth_lens.py build --base /opt/data/work/gt/ebtl_base.jpg --bbox 78.176867,12.727863,78.190131,12.740135
--a1 <the map's data.json> --out /opt/data/work/gt/lens.html` → a static HTML with the method toggle + a
cursor lens onto the 35 cm imagery, so the user eyeballs reality. Hand back the path. (Skip if no high-res
base is staged.) Then confirm at the top waypoints with `skyfi.py best --bbox <...> --cap-usd 50` (paid,
budget-guarded) — the paid step only narrows to the few points free layers can't resolve.

**Honest limit (always):** the map is *likelihood / suitability, not a confirmed ID*; nearest real records
may be far away (say how far — L1's `resolved` + the points `by_source`/`n` give you the numbers).
