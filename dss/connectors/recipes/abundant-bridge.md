# Recipe: follow the abundant dataset to build a case for more (the scarcity hook)

The most powerful move under scarcity: **anchor the answer in whatever dataset is most abundant for this
site, bridge it to the question via known ecology, then convert the gap into a concrete data ask.** Never
assume which dataset is abundant — CHECK (count what each source returns: `ebird` species, `points`/GBIF
records, `paper_data`).

1. **Bridge the abundant data via ecology.** e.g. if BIRDS are abundant (EBTL: 136 eBird species, ~0
   direct plant records) and the question is about plants/invasives/connectivity: `ebird.py dispersers
   --loc <hotspot>` → the frugivores that disperse seeds (incl. Lantana) = a mechanistic spread +
   corridor signal even with no plant data. (Generalises to any abundant source + its correlates.)
2. **Fill missing fields yourself.** eBird has no habitat field — annotate bird points with
   `landcover.classify` / `terrain.at` to recover "what landscape they use".
3. **State it as a correlation, honestly** — a bridge/hypothesis from the data we have, NOT an authority claim.
4. **Ask for the data that would confirm it** — the point is to instigate action (survey fruiting plants at
   bird-dense spots, log habitat on eBird, acoustic hardware, higher-res HS).

For **EBTL birds:** hotspot `L36453021`; `ebird.py hotspot --loc L36453021` anchors the site coords,
`ebird.py obs --loc L36453021` gives per-site bird points (finer than GBIF; needs a free key).
