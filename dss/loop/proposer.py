"""Proposer — turns an AOI's weighted buckets into candidate questions.

Each template carries: its primitive_shape, the connectors it needs, and a
`chain` — an executable gold recipe (produce -> annotate -> group) the driver can
run to mint gold, or None when the question needs an input point set / a connector
that doesn't exist yet. Frontier-grade generation (an LLM Proposer) can replace
these templates; they keep the POC deterministic and testable.
"""

_INVASIVE_MARKERS = ("lantana", "prosopis", "chromolaena", "parthenium", "mikania",
                     "ageratina", "senna", "eichhornia", "juliflora")

# bucket -> list of (template, primitive_shape, connectors, chain)
# {label}=AOI label, {invasive}/{flagship} filled per AOI. chain uses those too.
TEMPLATES = {
    "invasives": [
        ("In what land cover does {invasive} mostly occur around {label}?",
         "FIND -> LOOK_UP -> GROUP", ["occurrence", "landcover"],
         {"produce": "occurrence", "species": "{invasive}", "annotate": "landcover", "group": "landcover"}),
        ("Over what elevation range has {invasive} spread around {label}?",
         "FIND -> LOOK_UP -> GROUP", ["occurrence", "terrain"],
         {"produce": "occurrence", "species": "{invasive}", "annotate": "terrain", "group": "elevation"}),
    ],
    "biodiversity": [
        ("Where is {flagship} recorded around {label}, and in what land cover?",
         "FIND -> LOOK_UP -> GROUP", ["occurrence", "landcover"],
         {"produce": "occurrence", "species": "{flagship}", "annotate": "landcover", "group": "landcover"}),
    ],
    "governance": [
        ("Are {flagship} records inside or outside protected areas around {label}?",
         "FIND -> RELATE -> GROUP", ["occurrence", "protected_areas"],
         {"produce": "occurrence", "species": "{flagship}", "annotate": "protected_areas", "group": "in_pa"}),
    ],
    "fire": [
        ("Which parts of {label} are most exposed to fire?",
         "FIND -> SUMMARISE_IN_AREA -> RANK", ["fire"], None),   # needs an input point set
    ],
    "water": [
        ("Is greenness around {label} declining with distance from the reservoir "
         "(dry-season stress)?", "FIND -> TREND -> GROUP", ["greenness"], None),
    ],
    "restoration": [
        ("Which patches around {label} are greening (recovering) 2019-2024?",
         "FIND -> TREND -> GROUP", ["greenness"], None),
    ],
    # --- breaker primitives: no connector covers these yet ---
    "connectivity": [
        ("Are the forest patches around {label} connected enough for elephant "
         "movement between them?", "NETWORK (breaker — no connector yet)", [], None),
    ],
    "landuse": [
        ("How fragmented is the forest-cropland edge around {label}?",
         "PATTERN (breaker — no connector yet)", [], None),
    ],
}


def _roles(seed):
    invasive = next((s for s in seed if any(m in s.lower() for m in _INVASIVE_MARKERS)), None)
    flagship = next((s for s in seed if s != invasive), None)
    return invasive or (seed[0] if seed else "the invasive"), \
        flagship or (seed[0] if seed else "the flagship species")


def _fill_chain(chain, invasive, flagship):
    if not chain:
        return None
    return {**chain, "species": chain["species"].format(invasive=invasive, flagship=flagship)}


def propose(aoi, n=6):
    """Emit up to n candidate questions, ordered by bucket weight."""
    label = aoi["label"]
    invasive, flagship = _roles(aoi.get("seed_species") or [])
    out = []
    for bucket, _w in sorted(aoi.get("buckets", {}).items(), key=lambda kv: -kv[1]):
        for tmpl, shape, conns, chain in TEMPLATES.get(bucket, []):
            out.append({
                "bucket": bucket,
                "weight": aoi["buckets"][bucket],
                "question": tmpl.format(label=label, invasive=invasive, flagship=flagship),
                "primitive_shape": shape,
                "connectors": conns,
                "chain": _fill_chain(chain, invasive, flagship),
                "is_breaker": "breaker" in shape,
            })
    return out[:n]
