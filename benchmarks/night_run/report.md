# Night run — 36 questions

grounded 36/36 · used paper_data 8/36 · offered follow-up 21/36 · honest 17/36 · stuck 5 · errored 2 · avg 211s

## Per question

### Q0 [deepseek 95s] followup
**is lantana taking over our forest?**

connectors: ['inaturalist', 'invasive', 'phenology']

73 | 78.1946 | 0.58       | open maps        |
    | 4   | 12.7280 | 78.1965 | 0.57       | open maps        |
    | 5   | 12.7326 | 78.1811 | 0.55       | open maps        |
    
    A full field-navigable HTML map is at /opt/data/work/invasive/lantana_camara/map.html.
    
    Caveat: This is an invasive-likelihood map based on satellite phenology + transfer from regional records, not a confirmed Lantana ID. Evergreen natives in a dry-deciduous forest trigger the same "stays green" signal. Walking the waypoints is the ground-truth step.
    
    Want me to:
    1. Build a ground-truth lens so you can check these against high-res imagery before heading out?
    2. Run the same analysis for Jatropha or Dichrostachys (the ones already on site)?
    3. Check the land cover at these waypoint clusters to understand what habitat type is being flagged?

  hermes --resume 20260706_171535_4af732

### Q1 [deepseek 197s] paper followup
**what always grows near lantana?**

connectors: ['ecoregion', 'geo', 'invasive', 'occurrence', 'paper_data']

asives that thrive in disturbed forest edges and gaps. If you see Lantana, expect Siam weed nearby.
    - Teak is the native that grows most consistently alongside Lantana in this region. Lantana commonly invades under teak canopy gaps.
    - Lagerstroemia parviflora and Vitex altissima are the strongest native understory associates — they share the same dry deciduous habitat.
    
    Honest limit: This is presence-record proximity (coarse), not same-plot confirmation. A plant growing within 5 km of Lantana isn't necessarily sharing the same square metre — it shares the same habitat type. For plot-level co-occurrence, I'd need paper_data (ground-truthed plot lists) or field transects.
    
    Want me to dig deeper on any of these — e.g. check paper_data for actual plot co-occurrence records, or run the invasive map for Chromolaena at your site?

  hermes --resume 20260706_171710_21df8e

### Q2 [deepseek 92s] followup
**show me where the lantana is on our land**

connectors: ['inaturalist', 'invasive', 'occurrence', 'phenology', 'points', 'skyfi']

ery (6-band, 10m). It combines two signals: (1) what the area looks like spectrally where Lantana is known, and (2) multi-year stay-green behaviour (Lantana stays green through dry season while native deciduous trees drop leaves). The top patches are on the eastern edge (78.19+) and western boundary (78.17) of your site.
    
    Honest limit: This is a likelihood map, not a species ID. It flags patches that look like Lantana habitat. Some could be other evergreen invasives (e.g. Prosopis) or dense evergreen natives. To confirm: GPS the top 3-5 waypoints on foot, or buy one SkyFi high-res scene (~$15-50) to eyeball them from above.
    
    Next step: Want me to show a satellite-NDVI zoom on these hotspots, or cross-reference with the EBTL invasive profile in the reference docs? You can also open the map.html directly in a browser and pan around.

  hermes --resume 20260706_172027_8e864a

### Q3 [deepseek 114s] followup
**is prosopis or parthenium spreading near us?**

connectors: ['inaturalist', 'invasive', 'landcover', 'occurrence', 'phenology', 'points', 'skyfi']

/opt/data/work/invasive/parthenium_hysterophorus/map.html
    - Each has 15 GPS waypoints with lat/lon and Google Maps links
    
    Honest limits: The occurrence records stop ~15–39 km from site — no one has logged these species directly at EBTL on iNaturalist/GBIF. The likelihood map is a transfer from regional training data onto the site's satellite imagery, not an observation. Also, the EBTL bbox is small (~2.9 km), so the site's true diversity of invasives is likely under-sampled.
    
    If you want to go deeper:
    1. Want me to check the reference invasives profile (ebtl-invasives-profile.md) for prior mapping notes?
    2. Want to confirm these patches with a high-res scene (SkyFi, $50 budget)? I can price one.
    3. Want a habitat driver analysis (elevation, slope, landcover preferences) for these species to guide control strategy?

  hermes --resume 20260706_172159_a07661

### Q4 [deepseek 420s] STUCK
**which native trees should I collect seed from right now?**

connectors: ['inaturalist', 'occurrence', 'phenology']

cies fruits. Let me check all the key native trees for the region.
    

    Here's the picture from GBIF/iNaturalist phenology data. I checked 17 native dry-deciduous species for the EBTL corridor. Here's what's seed-ready right now (July) and what's coming:
    
    
    
    SEED COLLECTION NOW — July 6, 2026
    
    Top picks this month (have July fruiting records):
    
    1. Diospyros melanoxylon (Tendu/Kendu)
       - July fruiting confirmed — 2 of 14 annotated records
       - n=235 total records across India, n_annotated=14 (moderate confidence)
       - Also fruits Apr-May. July is a second good window.
       - Key dry-deciduous species for the site
    
    2. Lagerstroemia parviflora (Crape Myrtle)
       - 1 July record, n_annotated=14 overall
       - Also fruits Mar-Apr peak. Extended tail into monsoon
       - Strongest co-occurrence signal with Lantana in the corridor

### Q5 [deepseek 190s] paper followup
**when do the amla and tamarind here fruit?**

connectors: ['inaturalist', 'occurrence', 'paper_data', 'phenology']

tation (Jan=1, Mar=1, May=1). That's essentially noise — can't give you a reliable fruiting window from crowd-sourced data.
    
    
    
    Caveats:
    - This is crowd-sourced GBIF/iNaturalist phenology, observer-biased and month-binned — it's a rough timing guide, not a definitive calendar.
    - Both species have 300+ occurrence records in the wider donor belt (Krishnagiri–Bandipur corridor), so they definitely grow in this region. But nobody with a camera tagged the fruit stage on most of those observations.
    - To tighten this, the best source would be local nursery/forest-department seed-collection records or field notes from the EBTL team — a single season of field observations would beat the GBIF data for amla. I can also run a nursery-seed-timing report if you want to plan around the Krishnagiri NE monsoon (Oct–Dec planting window).

  hermes --resume 20260706_173052_604615

### Q6 [deepseek 420s] STUCK
**which mother trees should we protect for seed?**

connectors: ['occurrence', 'phenology', 'points', 'predict']

Let me check what native tree species are actually recorded near the site and their fruiting timing

    Now let me check if the site's habitat is suitable for the most promising species

### Q7 [deepseek 284s] STUCK followup
**what natives should we grow in the nursery for dry scrub?**

connectors: ['ecoregion', 'landcover', 'occurrence', 'phenology', 'predict', 'terrain']

n (pre-monsoon 2027 plan):
    - Neem and Cassia have the most records nearby (301 each) — easiest to find mother trees, collect seed May–June 2027, germinate through summer, plant with the NE monsoon
    
    
    
    My recommendation for a first nursery batch
    
    Top 5 to start right now:
    1. Albizia amara — nitrogen-fixer, dry scrub specialist, fruits next month
    2. Acacia nilotica — abundant nearby (226 records), thorny structure-builder
    3. Wrightia tinctoria — 200 records, fruits Sep, coppices
    4. Capparis sepiaria — collecting seed NOW, pollinator-friendly
    5. Azadirachta indica — abundant, drought-proof, establish for next season
    
    Want me to predict which of these have the best climate-match to your specific AOI? I can run predict.route to transfer the donor occurrence records and see which species' modelled suitability is highest at your exact site.

### Q8 [deepseek 420s] STUCK
**which saplings will survive our dry summers?**

connectors: ['ecoregion', 'greenness', 'landcover', 'occurrence', 'phenology', 'points', 'predict', 'terrain']

as suitable for your specific site.
    
import csv
# Check what's recorded near EBTL - use a medium bbox
w,s,e,n = 77.4,11.9,78.5,12.9
# Butea recorded in tighter AOI
print('=== Butea monosperma in EBTL AOI ===')
with open('/opt/data/work/ebtl_butea.csv') as f:
    rows = list(csv.DictReader(f))
    for r in rows[:5]:
        print(f'  lat={r[\"lat\"]}, lon={r[\"lon\"]}, year={r.get(\"year\",\"?\")}, source={r.get(\"dataset\",\"?\")}'[:120])

# Check what drought-tolerant trees are recorded in the wider corridor
print()
# Check greenness detail
with open('/opt/data/work/ebtl_greenness.csv') as f:
    rows = list(csv.DictReader(f))
    vals = {}
    for r in rows:
        tc = r.get('trend_class','')
        sl = float(r.get('ndvi_slope',0))
        vals[tc] = vals.get(tc,0)+1
    print('=== Greenness ===')
    for k,v in sorted(vals.items()):
        print(f'  {k}: {v} points')
"  0.0s

### Q9 [deepseek 306s] paper
**what do the elephants here eat?**

connectors: ['ebird', 'ecoregion', 'greenness', 'inaturalist', 'landcover', 'occurrence', 'paper_data', 'phenology', 'points', 'predict', 'terrain']

ndinacea)
    Records in Region: 18
    Near Site: Highly preferred
    
    These are all well-known elephant food plants — figs (highly preferred fruit), Terminalia (bark/leaves), Ziziphus (fruit), bamboo (shoots/stems), and Grewia (browse).
    
    The honest limit: What I've shown is available food plants, not direct diet observations at your site. A pregnant elephant and a bull use different forage, and seasonal shifts (dry vs. wet, fruiting vs. not) matter. Satellite and occurrence data can't tell you what they actually ate here — that needs direct sign surveys (dung analysis, feeding signs on vegetation).
    
    Want to go deeper?
    - I can predict route the suitability of specific food plants to your exact 70-acre site
    - Run phenology on food plants to see what's fruiting now
    - Or check eBird frugivores that overlap with elephant food plants for forest health signals

### Q10 [deepseek 288s] 
**where do elephants move through our area?**

connectors: ['geo', 'inaturalist', 'landcover', 'occurrence', 'points', 'predict', 'protected_areas', 'terrain']

So if connectivity improved, the habitat itself is fine.
    
    Your site's habitat is good for elephants (if they could reach it): 92% natural cover — 52% shrubland, 40% tree cover, 4% grassland. Only 4% cropland.
    
    
    
    Caveat: This is iNaturalist data only — opportunistic observations by naturalists, not systematic surveys. Elephants could pass through at night or in seasons with fewer observers. The 2024-2026 period has 16 recent records showing active presence in the western corridor, which is encouraging for the broader landscape.
    
    What would sharpen this answer: Camera trap data at your site (zero cost to ask — just deploy a few camera traps for 3 months). If you have camera trap data or can share boundary files of your restoration patches, I can run per-patch analysis. Systematic elephant dung surveys along transects would also confirm or deny actual usage.

### Q11 [deepseek 311s] paper followup
**are elephants likely to raid crops near the village?**

connectors: ['ecoregion', 'greenness', 'inaturalist', 'landcover', 'occurrence', 'paper_data', 'phenology', 'points', 'predict', 'terrain']

— they miss transient crop-raiding visits
    - No crop-raiding surveys or conflict data from paper_data for this specific area
    - Satellite can't distinguish crop types or maturity stage (key raiding attractants)
    - The nearest elephant at 4.4 km could be seasonal or a regular
    
    Concrete next step if you want sharper:
    Mark crop areas, guard-hut locations, and any raiding events (past season, GPS coordinates) on a map — even a hand-drawn one photographed — and I'll run a distance-to-village / distance-to-forest-edge analysis to flag the highest-risk patches. For the seasonal timing, the phenology connector can tell you when local elephant-favoured crops (maize, sugarcane, if present) mature relative to dry-season elephant movement.
    
    Want me to map the elephant points vs cropland in the AOI, or check the greenness trend (forest degradation) near the village edge?

### Q12 [deepseek 186s] followup
**where do elephants and people overlap most?**

connectors: ['greenness', 'inaturalist', 'landcover', 'occurrence', 'points', 'protected_areas']

s
    
    Your EBTL site: The closest elephant record is 6.5 km southeast (in shrubland). No direct overlap with people recorded at the site itself — likely because it's a small degraded patch in a valley with less movement corridor than the Hosur edge.
    
    Honest caveat: These are observation records (iNaturalist/GBIF) — people report elephants where people ARE, so there's some observation bias. Satellite can see the landcover but not the actual encounter frequency or crop damage. Also, no WDPA protected-area boundaries cover this corridor, so I can't say which records are inside/outside reserves.
    
    To sharpen this: If you have village-level conflict reports, crop-raiding data, or seasonal movement maps from the Forest Department, I can overlay those. Want me to also check greenness trends near the hotspot zones — are the forests these elephants use recovering or degrading?

### Q13 [deepseek 410s] followup
**which birds tell me our forest is getting healthier?**

connectors: ['ebird', 'greenness', 'indicators', 'landcover', 'occurrence']

woody regrowth (easy: acoustic survey)
    
    Bottom line
    The healthiest signal is a swap: less Common Myna/House Crow, more Junglefowl/Paradise Flycatcher/Pitta. Specifically:
    1. Grey Junglefowl returning = leaf litter recovering
    2. Hornbill returning = large trees with cavities (slowest signal, biggest win)
    3. Butterfly diversity (already tracked) = host plants coming back
    
    What would sharpen this
    - Get an eBird API key (free, 2 min) — then I can pull the full bird list for EBTL hotspot L36453021 and tell you exactly which indicators are already there vs. missing
    - Set up point counts in different habitat patches — annual comparison tracks recovery
    - Send me a CSV of your sightings with lat/lon and I'll annotate them with landcover and greenness trend
    
    Want me to check a few specific species at the site if you can get that eBird key set up?

### Q14 [deepseek 307s] paper
**which birds spread seeds here?**

connectors: ['ebird', 'inaturalist', 'indicator', 'indicators', 'landcover', 'occurrence', 'paper_data', 'points']

ng as the canopy matures.
    
    Ecological signal from the indicators connector: Bulbuls (Pycnonotidae) are identified as the key connectivity indicator — seed dispersal between habitat patches — with 300+ GBIF records in your corridor. Hornbills are also listed as long-distance seed dispersers, found regionally.
    
    Limits: This is occurrence data (GBIF + iNaturalist), so it shows where birds were observed, not a full diet study. The eBird API key isn't configured — if you set one up (free at ebird.org/api/keygen), I can pull the full eBird hotspot list for EBTL (L36453021) with their disperser-specific analysis, plus annotate their points with landcover to see which habitat each species uses on your site.
    
    A concrete next step: Set up the free eBird API key and I'll give you the complete disperser analysis — which birds eat which fruits, mapped to your site's landcover.

### Q15 [deepseek 420s] STUCK
**where do the birds and the fruiting trees overlap?**

connectors: ['ebird', 'inaturalist', 'occurrence', 'points']

looking at what data and reference lists we already have

    Let me check eBird availability and start gathering data on birds and fruiting trees.
    

    eBird API key isn't set — no direct site bird list. But I can use GBIF/iNaturalist data through the points resolver instead. Let me check what fruiting trees and frugivorous birds have records in the donor belt, and where they co-occur.
    

    Good — solid records for all the key fruiting trees. Now let me get the frugivorous bird data to find overlaps

    Bird data has too many records for the donor belt in 30s. Let me use a tighter bbox — the corridor AOI — and the occurrence connector directly

    All birds have ~300 records each in this corridor. Now let me pull the same fruiting tree records in the corridor bbox so we can compute co-occurrence at the gold-standard site scale. Also let me grab a couple more key frugivores.

### Q16 [deepseek 133s] 
**which of our ponds dries up first?**

connectors: ['landcover', 'occurrence', 'water']

omes back every year)
    Rank: 10
    Area: Pond 8 (W)
    Seasonality: 3 mon/yr
    Occurrence: 19%
    Notes: Bare/sparse veg zone
    Rank: 11
    Area: Main lake (center)
    Seasonality: 5 mon/yr
    Occurrence: 28%
    Notes: Holds longest
    
    Key finding: 6 of 11 ponds hold water only ~1 month/year — they're ephemeral. The northeast pond (Pond 0) is the most precarious: lowest occurrence (3%), cropland setting (likely direct evaporation + draw for irrigation).
    
    Honest caveat: JRC at 30m misses farm/check-dams under ~30m — many of your actual restoration ponds may be smaller than that and aren't in this analysis. If you send me a CSV with your ponds' GPS waypoints (lat/lon), I can run the exact same water persistence check on them. The numbers above are a 38-year satellite average — this year's actual may differ with rainfall.

  hermes --resume 20260706_183109_179d7f

### Q17 [deepseek 46s] followup
**how much water is in our ponds through the year?**

connectors: ['greenness', 'occurrence', 'points', 'water']

ll the real story for the current restoration.
    - Smaller farm ponds < ~30 m across are missed entirely — if you've built or restored smaller ponds/check-dams, they won't show in this data. If you send me a CSV of your pond locations with lat/lon, I can annotate each one with its seasonal profile using the full JRC record.
    - The single waterbody is the lake itself — any ponds on the 70 acres that are too small or vegetation-shaded would be invisible at this resolution.
    
    Follow-ups I can do:
    1. Run water.py at --points <your pond CSV> if you have GPS coordinates for specific ponds you've dug/restored
    2. Pair with dry-season greenness (Sentinel-2 NDVI) to show which areas around the pond stay stressed longest after the water dries
    3. Zoom out to the wider corridor to see how many other water sources exist in the landscape

  hermes --resume 20260706_183322_05950f

### Q18 [deepseek 88s] 
**is our forest actually coming back?**

connectors: ['greenness', 'landcover', 'points', 'predict']

lot with its surroundings. So some of that greening signal could include roadside vegetation or farm tree cover just outside your boundary.
    - The landcover map is 2021 — the trees you've planted in the last couple of years may show up as "shrubland" because they haven't grown tall enough yet to register as "tree cover" from space.
    - This measures overall greenness, not species composition. Novel ecosystem vs native mix = satellite can't tell; that needs ground plots.
    
    To sharpen this for YOUR specific 70 acres, send me the patch boundaries (GeoJSON or KML) and I'll clip the analysis to just your restoration area — the numbers should be even stronger when we remove the boundary cropland pixels from the count. Also happy to run the predict connector to model which native dry-deciduous species are climatically suitable for your site.

  hermes --resume 20260706_183408_adce9a

### Q19 [deepseek 68s] 
**how thick is the canopy across our land?**

connectors: ['greenness', 'landcover', 'points', 's2']

els (typically 0.7+) — the canopy "thins" naturally in the dry season when leaves drop.
    
    Caveat: This is 10m satellite data, not field-measured canopy. A 10m pixel called "dense canopy" could be a single tree crown or a thicket of shrubs — it doesn't distinguish. The ~50% shrubland class means much of that "dense" signal is scrub, not tall timber. For finer canopy measures (LAI, % bare ground beneath canopy, tree vs. shrub stratification), send me your plot boundaries or a CSV of sampling points and I'll run s2.py at to get per-location NDVI + cover class.
    
    Want to go deeper?
    - Compare wet vs. dry season NDVI to see how much canopy drops in summer
    - Map the spatial pattern of canopy density (which patches are thinnest?)
    - Check whether the denser canopy corresponds to the restoration planting areas vs. natural regrowth

  hermes --resume 20260706_183536_264311

### Q20 [deepseek 274s] 
**what trees do we have on the site?**

connectors: ['ebird', 'ecoregion', 'geo', 'inaturalist', 'invasive', 'landcover', 'occurrence', 'points', 'predict', 'water']

nor records
    - Manilkara hexandra, Flacourtia montana, Grewia tiliifolia — also regionally known
    
    
    
    Bottom line for the site:
    
    The AOI has 34% tree cover (satellite measure). The actual tree species confirmed by observations on-site are: Butea monosperma, Cassia fistula, Gyrocarpus americanus, Schrebera swietenioides, and Holoptelea integrifolia. About 12+ more native dry-deciduous species are well-documented in the surrounding corridor and would be ecologically suitable for planting/restoration.
    
    Caveat: These are satellite + iNaturalist observations — not a plot-level inventory. The iNaturalist data covers only ~20 records across the ~70-acre site, so many trees growing here may not have been logged yet. For a complete species list at the planting-patch level, send me your plot boundaries or field survey sheets and I can compute per-patch composition.

### Q21 [deepseek 135s] followup
**which insects or creatures signal healthy soil?**

connectors: ['inaturalist', 'indicators', 'points']

ace near cattle/wildlife trails)
    - Ants → simple pitfall traps or Winkler extractors from leaf-litter samples
    - Springtails → Berlese funnel extraction from soil cores (very small, need a hand lens)
    
    The presence of all three (especially dung beetles and springtails, which vanish under compaction/pesticide) is a strong signal soils are recovering their biological function. If you can't do all three, ants alone are the cheapest and most robust single indicator — the literature (Andersen 1997) has a well-tested protocol for using ant functional groups to score restoration progress.
    
    
    
    Want me to check what ants species are recorded in the wider corridor (855 records) so you know what to expect? Or run the same indicators for forest recovery (butterflies, spiders, cicadas) — your team already tracks arachnids at EBTL.

  hermes --resume 20260706_184311_69f6b5

### Q22 [deepseek 156s] 
**are dung beetles or ants around that show recovery?**

connectors: ['greenness', 'indicators', 'landcover', 'occurrence']

cords — closest is Oecophylla smaragdina (weaver ant) at ~45 km from site. None within 20 km.
    
    In short: neither group has been systematically surveyed at EBTL. The closest recorded dung beetle is ~15 km away, the closest ant ~45 km. That doesn't mean they aren't there — it means nobody has pitfall-trapped or iNat-recorded them at your site.
    
    The one arthropod indicator your site already tracks is spiders (Araneae) — EBTL has 1 GBIF record, and spiders signal vegetation structure & microhabitat recovery. That's a good start.
    
    Best next step: Set up a targeted insect survey — dung-beetle pitfall traps along a disturbance gradient and ant transects in recovering vs. undisturbed patches. If you have plot boundaries or transect locations you'd like me to check satellite landcover/greenness on for survey design, I can run that.

  hermes --resume 20260706_184526_b17d69

### Q23 [deepseek 91s] followup
**where is the soil most degraded on our land?**

connectors: ['greenness', 'landcover', 'points', 'terrain']

(3 small patches ~6% of area)
    The only human-modified soils — near the lake/farm boundary. These are on gentle slopes (2-5°) so erosion risk is low, but soils are likely compacted from cultivation.
    
    The good news: 96% of your site is naturally vegetated and actively greening. There's no declining, bare, or degraded-dead zone. The restoration work is clearly taking hold.
    
    Caveat: This is satellite-scale (10m landcover, 250m greenness trend). I can't see micro-degradation like surface crusting, gully initiation, or nutrient depletion between trees. If you have GPS boundaries of specific treatment patches or erosion-prone gullies, send me a CSV and I'll compute per-patch soil-health proxies (NDVI trend, slope, landcover) at their exact locations.
    
    Want me to map these top priority spots with GPS waypoints you can walk to?

  hermes --resume 20260706_184801_6eaba8

### Q24 [deepseek 210s] ERR followup
**where would new trees survive best if we plant this monsoon?**

connectors: ['landcover', 'points', 's2', 'terrain', 'water']

- The mid/high slopes (above 620m, mean slope 15-17 deg) — water runs off fast, erosion risk, harder for saplings to establish
    - Dense canopy areas (71% of site is already tree-covered per S2) — no point planting under existing canopy
    
    The honest limit: This is a satellite-proxy analysis (30m SRTM + 10m S2). I'm using NDVI as a proxy for soil moisture/condition, not measuring it directly. For your specific planting survival question, the ideal data would be:
    - Soil moisture maps (Sentinel-1 SAR) — would show actual wetness patterns during the monsoon
    - Your planting plot boundaries — if you share a CSV with lat/lon of the specific patches or pits you're considering, I can score each one individually rather than the 80m grid
    
    Want me to export the top-100 ranked GPS spots as a field-navigable file? Or score a specific set of patches you already have in mind?

### Q25 [deepseek 142s] followup
**is there a wildlife corridor through our land?**

connectors: ['ecoregion', 'geo', 'inaturalist', 'indicators', 'landcover', 'points', 'predict', 'protected_areas', 'terrain']

orest block (west/north). The EBTL site itself is a natural stepping stone — but connectivity northwards and eastwards is pinched by cropland.
    
    Bridging from what's abundant here: Bulbuls (frugivores / seed dispersers) have 105 GBIF records near your site — they're actively moving seeds between whatever patches exist. That's a positive signal for corridor function even in the fragmented zones.
    
    Honest limit: This is from 300 satellite sample points across a 1°×1° area at 10m resolution — good for the landscape-scale pattern, but not a fine corridor model. A formal connectivity analysis (Circuitscape or similar) using your patch boundaries + resistance surfaces would give you per-patch permeability scores. Want me to generate that? Also happy to map the likely elephant movement routes relative to your specific land boundaries — just share a boundary file (GeoJSON/KML/CSV).

### Q26 [deepseek 126s] followup
**what connects our forest to the bigger forest?**

connectors: ['ebird', 'greenness', 'landcover', 'points', 'protected_areas', 'skyfi']

In short: EBTL is separated from the bigger Cauvery/BR Hills forest by ~40-50 km of cropland and Hosur's urban sprawl. There's no continuous green corridor. The northward scrub is greening but stays as isolated tree/shrub patches. The best connectivity signal is southwest, but it would need active corridor restoration across the farmland gap.
    
    Follow-ups I can help with:
    1. Map the exact corridor route — generate a detailed landcover map of the shortest green route toward Cauvery sanctuary
    2. eBird disperser birds — check which seed-dispersing birds move through EBTL (they're the natural corridor builders)
    3. Greenness trend map of the whole corridor to see where restoration would have the most impact
    4. Higher-res (SkyFi) imagery for a specific bottleneck — priced, budget-guarded at $50 max
    
    Want any of these?

  hermes --resume 20260706_185525_885b9b

### Q27 [deepseek 93s] followup
**has there been fire near us recently?**

connectors: ['fire', 'points']

-days: 7
    Closest to us: ~6 km NE (12.86, 78.23)
    
    So fires have occurred in the broader landscape — the closest historical fire was about 6 km northeast of the site in the 2020–2023 period. In 2024–2025, all fires have been 45+ km southwest, none near us.
    
    Honest limits: This is MODIS MOD14A1 at ~1 km resolution — it only catches thermal anomalies large/hot enough to register in a 1 km pixel. Small, brief, or cool-season ground fires (e.g., grass fires burning through quickly at night) can be missed entirely. It's a coarse safety signal, not a fine detection system.
    
    Best next step if you're concerned: Field staff can record any observed fire scars or burn evidence on the monthly patrol log, or we could annotate a set of monitoring points with fire.exposure to quantify cumulative fire risk per zone. Want me to run that?

  hermes --resume 20260706_185731_a74cb2

### Q28 [deepseek 215s] followup
**where are the fire-prone patches?**

connectors: ['fire', 'landcover', 'points', 'skyfi']

.
    
    Fire follows fuel type: cropland (100%), grassland (100%), and open shrubland (44%) burn far more than tree cover (14%). The west is open/degraded — shrubland + agriculture with sparse canopy — while the east has more intact tree cover that buffers fire.
    
    The honest limit: MODIS is ~1 km resolution, and the absolute fire counts are low (max 1.1 fire-days over 10 years across the whole site). This means fires are infrequent but concentrated in the western wedge. At this resolution, individual small fires within the 70-acre site blur together; actual burn patches could be smaller than a pixel.
    
    What would sharpen this: a higher-res layer (Sentinel-2 burn scars at 10 m or SkyFi imagery at 50 cm) would show exact burn scar boundaries. Want me to pull Sentinel-2 imagery for the western strip to map actual burn scars at 10 m?

  hermes --resume 20260706_185904_3260f6

### Q29 [deepseek 166s] 
**which weeds besides lantana should we watch for?**

connectors: ['fire', 'inaturalist', 'invasive', 'occurrence']

n.
    - Opuntia stricta (Erect Prickly Pear) — 25 records in corridor, ~15 km out. Forms impenetrable thickets, spines injure wildlife.
    - Prosopis juliflora (Mesquite) — 3 records in the corridor, ~39 km away. Still sparse but a known invasive in TN drylands.
    
    Notable: Lantana is 21 km away — 300 records in the donor belt but none at the site. That's unusual for dry deciduous forest. It may arrive eventually via birds or machinery, so keep monitoring edges.
    
    Caveat: These are iNaturalist research-grade observations, not a systematic botanical survey. A field walk would likely find more, especially at edges and disturbed patches. If you want to send me a CSV of your plot boundaries or survey transects, I can run the invasive connector's RandomForest model to generate a likelihood map and GPS waypoints for any specific species.

  hermes --resume 20260706_190239_78f593

### Q30 [deepseek 294s] followup
**what fruiting plants feed birds in the dry season?**

connectors: ['ebird', 'inaturalist', 'occurrence', 'phenology', 'predict']

ecords in donor belt): Flacourtia montana, Securinega leucopyrus — these may occur in the area but GBIF hasn't captured them.
    
    Honest caveats:
    - Phenology data is from crowd-sourced GBIF/iNaturalist records, not systematic monitoring at your site. Month bins are approximate.
    - eBird connector is disabled (no API key) — I couldn't confirm which specific frugivores are recorded at the EBTL hotspot (L36453021). Get a free eBird key and I'll match each plant to actual bird species seen at your site.
    - For plot-level confirmation at your specific 70 acres, send a boundary file and I can model suitability for each of these species.
    
    Want to do next? I can run predict.route to check if these species are modelled as suitable for your specific site bbox, or search for any specific bird-frugivore lists if you have the eBird key.

  hermes --resume 20260706_200917_09e894

### Q31 [deepseek 211s] ERR
**where are the rocky or bare patches we should leave alone?**

connectors: ['greenness', 'landcover', 'points', 's2', 'terrain', 'water']

reas of bare/rocky ground that need to be fenced off and left alone. The 55 small thin-veg spots (< 30 cm each) are scattered, not block-level. What's more relevant for restoration planning is differentiating the 29% sparse/scrub areas (which DO need planting) from the 71% dense canopy (which is already forest).
    
    What I saved
    - /opt/data/work/ebtl_rocky_waypoints.csv — GPS waypoints (lat/lon) for the bare/built + very-low-NDVI spots if you want to walk them.
    
    Caveat
    This is 10 m Sentinel-2 resolution — individual boulders or rock sheets smaller than ~10×10 m won't show up. If you have specific patches in mind (say 5–50 m rocky outcrops you know about), send me their boundaries and I'll compute per-patch stats. For a field check, walking the waypoints in the rocky_waypoints.csv file with a GPS will confirm what's actually exposed rock vs just thin dry-season grass.

### Q32 [deepseek 240s] 
**is the climate here still suitable for our native species?**

connectors: ['ecoregion', 'greenness', 'landcover', 'occurrence', 'points', 'predict', 's2']

tion gap, not a climate shift.
    
    Greenness tells the real story — 96% of the site is greening (mean NDVI slope +0.0133/yr), 4% flat, 0% browning. MODIS annual trend. The recovery is well underway.
    
    Bottom line: Climate has NOT shifted out of suitability for our native dry-deciduous species. The limiting factor is the current landcover state (shrubland → needs canopy development), exactly what the restoration is addressing. Plant your natives — Dhon, Kino, Teak, Crape Myrtle, Rosewood — the climate will support them.
    
    Caveat: These are modelled climate envelopes, not field-verified. WorldClim bioclim data is 1 km resolution (coarse). For your exact 70-acre patches, I'd need plot boundaries to do a finer S2-derived microclimate check. Also, if you have specific local species you're propagating at the nursery, I can run the same check on each one — just send the list.

### Q33 [deepseek 63s] paper followup
**what data are we missing to answer all this well?**

connectors: ['ebird', 'fire', 'greenness', 'hyperspectral', 'inaturalist', 'indicators', 'invasive', 'occurrence', 'paper_data', 'phenology', 'points', 'predict', 'skyfi', 'terrain', 'water']

rce — birds, dispersers, indicators
    Fix: Dryad OAuth
    Effort: 5 min (free)
    Impact: Unlocks ~50% of plot-level research data
    Fix: SoilGrids connector
    Effort: ~30 min to build
    Impact: Adds soil pH, OC, N, texture at 250 m for free
    Fix: Field survey (botanical)
    Effort: ~2 person-weeks
    Impact: The only ground truth that matters — validates everything else
    Fix: Dry-Deccan plot crawl
    Effort: ~2 h targeted search
    Impact: Better absence data + transfer quality
    Fix: Household/livelihood survey
    Effort: 1–2 months
    Impact: Answers the questions satellites can't
    
    
    
    Want me to build any of these? The SoilGrids connector and Dryad credentials setup are things I can do right now. For the eBird key, you just need to visit ebird.org/api/keygen and paste it into ~/.hermes/secrets/ebird.json.

  hermes --resume 20260706_191952_b6491b

### Q34 [deepseek 225s] paper followup
**where would sandalwood grow on our land?**

connectors: ['inaturalist', 'landcover', 'occurrence', 'paper_data', 'predict', 'terrain']

— it latches onto host roots. Your steeper slopes (the majority of the site) don't match its profile well. The ~2% of suitable area would most likely be on your flattest, most tree-covered pockets — the gentler valley-bottom patches where tree cover is densest, not the open shrubby slopes.
    
    
    
    Bottom line: Sandalwood is not a strong candidate for mass planting here, but if you want to trial it, focus on the flattest, tree-rich valley-floor spots. It's a partial root parasite — needs a host tree nearby (most recorded near Albizia, Acacia, Lantana — any woody perennial works). 
    
    Want me to: 
    1. Map those ~2% modelled-suitable spots on a satellite base so you can scout them on foot?
    2. Check if sandalwood's host trees are already at the site?
    3. Compare with better-suited native timber species for your slope/soil?

  hermes --resume 20260706_192055_0492a0

### Q35 [deepseek 195s] paper followup
**what grows near the water that elephants use?**

connectors: ['ecoregion', 'landcover', 'occurrence', 'paper_data', 'water']

15% grassland — they forage across the mosaic, using tree patches for cover and crop fields (like ragi, maize) as food near water sources.
    
    The honest picture: The lake is too seasonal to support moisture-loving riparian species year-round. What grows near it is typical dry-deciduous forest — Anogeissus latifolia, Albizia amara, Acacia, Ziziphus (typical of this ecoregion, though not verified at the site specifically). Since the EBTL site is data-poor for plants (few GBIF records), a stronger answer needs:
    
    1 concrete next step: Walk the lake perimeter and note which tree/shrub species are fruiting and showing elephant sign (dung, browse, tracks). Or run a focused plant survey along the 0.79 ha lake edge — that would tell you exactly what's available for elephants right there. Want me to map the elephant sighting locations near water bodies in the wider corridor instead?
