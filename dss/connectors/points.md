# points — the species→points resolver (one source-of-truth)

- **purpose:** turn a species NAME into a cached, source-merged points CSV. The ONLY place that knows the sources (GBIF `occurrence` + `inaturalist`), so adding a source = edit only this file.
- **produces:** a **deterministic** CSV path other tools consume — so the agent never invents a filename.
- **why:** stops the "hallucinated temp filename" failure — call `points.get`, pass the returned `path`.

**functions**
- `get(species, bbox=[w,s,e,n], sources=('gbif','inat'), limit=500, refresh=False) -> {path, n, by_source}`

**example**
```
python /opt/data/connectors/points.py get --species "Tectona grandis" --bbox 77.8,12.37,78.55,13.1
# -> {"path":".../points/tectona_grandis__<hash>.csv","n":..,"by_source":{"gbif":..,"inat":..}}
```
Tools like `geo.cooccur --a-species/--b-species` call this internally. Cache: `/opt/data/work/points/`.
Default bbox = dry-Deccan analog belt; `--refresh` re-pulls.
