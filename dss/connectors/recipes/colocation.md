# Recipe: species co-occurrence / colocation ("what grows / lives around X?")

A repeatable chain — don't hand-roll distances or invent point-file names.
1. **Find X** — `points.py get --species "<X>" --bbox <aoi>` (resolves the name; merges GBIF+iNat+paper).
2. **Hypothesise co-occurring species** from the ecoregion + the land cover of X's points (`ecoregion`,
   `landcover`) — this list is DOMAIN KNOWLEDGE → candidates to VERIFY, not fact.
3. **Confirm each candidate with data** (strongest → weakest):
   - `paper_data` **plot lists** = TRUE co-occurrence (same plot) — gold standard;
   - else `geo.py cooccur --a-species "<X>" --b-species "<candidate>" --bbox <w,s,e,n> --radius-km 5` →
     how many candidate records sit near X (a shared-habitat PROXY, presence-only; the resolver fetches +
     caches the points — do NOT create/name CSVs yourself);
   - if occurrence is too sparse → `predict` SDM-overlap (model both suitabilities, overlap the suitable
     areas = shared *habitat*, even without co-located records).
4. **Report** verified co-occurrences with the honest limit (proximity ≠ same-plot; presence-only).

For **predator/prey** specifically (snakes↔prey, spiders↔prey): the gold source is **diet studies in
`paper_data`** — gut-content and especially **stable-isotope** (δ¹³C/δ¹⁵N trophic-position) datasets give
the real trophic links; occurrence proximity is only a weak proxy. Lead with the paper, then proximity.
