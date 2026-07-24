# Recipe: papers-first (the researcher-grade path — beat their own literature review)

Our first users are **researchers**. If we only cite paper *titles* they'll think their own review is
better. We win by (a) checking the literature **first**, and (b) pulling the **presence points and values
embedded INSIDE the datasets** those papers publish — the part a manual review misses.

### 1. Search the corpus first (before any satellite guess)
```
python /opt/data/connectors/discovery.py search --query "<lay topic>" --points-only  # SEMANTIC — do this FIRST
python /opt/data/connectors/paper_data.py find --query "<topic>"        # our ingested Zenodo/Dryad corpus
python /opt/data/connectors/litscout.py works --query "<topic>" --kind dataset --india   # OpenAlex datasets
python /opt/data/connectors/litscout.py authors --query "<topic>"       # the co-authorship cluster (the lab)
python /opt/data/connectors/litscout.py expand --author "<seed>" --topic "<topic>"  # author->coauthors->datasets
```
Search several angles: the **taxon** (scientific AND common), the **region** (Eastern Ghats / the specific
hills / Tamil Nadu / Andhra), the **method** ("stable isotope", "phylogeography", "cave", "diet"), and
**higher taxa** (family/genus) when the species is data-poor. Also `paper_data.dryad_find` (authenticated).

**`discovery` is the SEMANTIC lever — run it FIRST for a lay/paraphrased ask.** It searches the ingested
corpus by MEANING over content cards (title + every column + codebook), so "weed taking over coffee" reaches
the dataset titled *"Brewing trouble: coffee invasion"* and "invasives near my seedlings" reaches a
*canopy-cover/fruit-removal of an invasive weed* dataset — matches keyword search buries or misses (bench
over 256 cards: MRR 0.40 vs 0.17, recall .58 vs .33 — right dataset ranked higher, robustly). One call, no keyword
fumbling; then feed the returned `doi` straight to `paper_data.extract --url <doi>` for the points inside.
Use `discovery` for the INGESTED corpus; `litscout` for live OpenAlex discovery of NEW papers.

**Walk the people, not just the titles (`litscout` — the researcher-beating move).** A title search finds
the famous paper; the **author co-authorship graph** surfaces the same lab's *other* papers and their
**archived datasets** (where the presence points live). Chain: `litscout authors <topic>` → pick a seed →
`litscout expand --author <seed> --topic <topic>` → co-authors + their **datasets** (DOIs) → feed each
dataset DOI to `paper_data.extract --url <doi>` for the **points inside**. This is how you beat a manual
review: you reach the archived data a keyword search never lists.

### 2. Pull the DATA out of the matching datasets — not just the title
```
python /opt/data/connectors/paper_data.py inspect --url <dataset_url>   # columns + codebook
python /opt/data/connectors/paper_data.py extract --url <dataset_url>   # detected coords + values -> points
```
- **Presence points inside a dataset** = confirmed occurrences → feed straight into `points`/`predict` as
  high-grade, ground-truth records (better than GBIF for these taxa).
- **Trait / diet / isotope / plot-census tables** → the drivers, the predator-prey links, the community
  context. A plot census that OMITS a species at a coord = a real ABSENCE (gold for SDMs).
- **Always have a human/judge confirm the column mapping** — column names vary wildly (the connector's gotcha).

### 3. Merge, then answer
`points.py get` already folds `paper_data` in with GBIF+iNat — so a species question automatically includes
paper points. State plainly: "from N papers (named) I found M dataset-embedded records + these
drivers/associates", then the honest limit + the one data ask.

### For taxonomy / phylogeny / conservation-status / diet-isotope questions — LITERATURE, not satellites
These are literature-shaped. **Lead with `paper_data` (2–4 targeted searches) + your knowledge, then STOP
and answer — do NOT grind `occurrence`/`landcover`/`greenness`/`predict` grids for a taxonomy or
phylogeny question** (that's the over-exploration that wastes 60+ tool calls for no gain). Report what the
papers establish (described species, type locality, phylogenetic placement, IUCN/WPA status, isotope/diet
findings, georeferenced material examined) + the gaps (undescribed diversity, no genetic data, no isotope
baseline) + the concrete ask (which specimens/sequences/surveys resolve it). A satellite layer only earns
its tool call if the question has a real spatial "where" component; otherwise skip it. Do NOT fabricate a
phylogeny/taxonomy from memory — cite the dataset/paper or label it unverified.
