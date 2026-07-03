# connector: protected_areas

- **purpose:** WDPA protected-area boundaries (via Earth Engine, no token).
- **when to use:** test whether points fall inside a protected area; list PAs in a region.
- **produces/annotates:** POINT annotator — adds `in_pa` (bool), `pa_name`.

**functions**
- `contains(points) -> + in_pa, pa_name`
- `names(bbox=[w,s,e,n]) -> [protected-area names]`

**⚠ coverage limitation (important):** WDPA polygon coverage in **India is
partial**. In the Western Ghats AOI the only boundary present is the fragmented
"Ghâts occidentaux" World Heritage site — major reserves (**Mudumalai TR,
Anamalai TR have NO boundary in WDPA**). So `in_pa=False` means *"no WDPA boundary
here"*, not necessarily *"outside all protected areas"*. For reliable
inside/outside-PA analysis in this AOI, **supply reserve boundaries as a GeoJSON
asset and use `geo.within` instead.** Surface this limitation to the user rather
than reporting a misleading inside/outside split.

**example**
```
python /opt/data/connectors/protected_areas.py contains --points occ.csv
```
