# connector: paper_data

- **purpose:** ingest the DATASETS/codebooks *inside* research papers (Zenodo/Dryad) —
  presence points, plot measurements, soil/traits — and return them like GBIF. The
  under-tapped source; feeds the transfer/interpolate algebra for proxy estimates.
- **when to use:** get the non-GBIF data (soil, plots, canopy, traits, NGO field records)
  for the AOI or a nearby/analog area.
- **produces:** POINT producer — points with a `value` + `value_type` + provenance (DOI).

**functions**
- `find(query|community='ncf') -> datasets with tabular files` (Zenodo)
- `dryad_find(query) -> Dryad datasets with per-file download urls` (AUTH — see below)
- `ingest(file_url) -> detected coords + value + points (VERIFY the mapping)`
- `ingest_dataset(dataset) -> handles multi-file (joins a value file to a coord file)`
- `search(variable, aoi_bbox) -> points tagged in_aoi | near_or_analog`

**communities:** NCF = c1433757-... (curated — use communities, NOT noisy full-text).

**Dryad = authenticated source.** Search/metadata are open, but downloading file BYTES
needs an OAuth bearer (`dryad_configured()` reports whether creds are set). Creds live
OUTSIDE the repo: env `DRYAD_CLIENT_ID`/`_SECRET`, or `~/.hermes/secrets/dryad.json`
(Hermes sandbox), or `~/.config/idlisseus/dryad.json` (host). Get them at
datadryad.org/account (ORCID login). Setup + validation: `benchmarks/algebra/research/
DRYAD_SETUP.md` + `dryad_check.py`; whole-repo check: `python3 preflight.py`. Without
creds, `dryad_find` still searches but downloads 401 and the connector warns loudly.

**example**
```
python /opt/data/connectors/paper_data.py find --community ncf
python /opt/data/connectors/paper_data.py ingest --url <zenodo file url>
```

**gotchas:** column names/value fields vary wildly; species is often in a free-text field;
some datasets are relational (coords in a separate file). ALWAYS have a human/judge confirm
the ingest mapping. Field-GPS coords are imprecise — pair with ground-truthing. Common vs
scientific names may need normalization for cross-source matching.
