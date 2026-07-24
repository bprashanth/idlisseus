This dataset contains animal roadkill data (2011-13) from the Valparai Plateau and Anamalai Tiger Reserve, Western Ghats, India. Occurrence records were gathered in the field by researchers of the Nature Conservation Foundation, India. The dataset corresponds to the following publication:

Jeganathan, P., Mudappa, D., Kumar, M. A., and Raman, T. R. S. 2018. Seasonal variation in wildlife roadkills in plantations and tropical rainforest in the Anamalai Hills, Western Ghats, India. Current Science 114(3): 619-626. DOI: 10.18520/cs/v114/i03/619-626

CONTACT #1
1. Name: P. Jeganathan
2. Work Address: Nature Conservation Foundation, 1311, 12th A Main, Vijayanagar 1st Stage, Mysuru 570017, Karnataka, India
3. Work Phone: +91 821 2515601
4. Email address: jegan@ncf-india.org 
5. ORCID: https://orcid.org/0000-0002-0238-0655

CONTACT #2
1. Name: Divya Mudappa 
2. Work Address: Nature Conservation Foundation, 1311, 12th A Main, Vijayanagar 1st Stage, Mysuru 570017, Karnataka, India
3. Work Phone: +91 821 2515601
4. Email address: divya@ncf-india.org 
5. ORCID: https://orcid.org/0000-0001-9708-4826

CONTACT #3
1. Name: M. Ananda Kumar
2. Work Address: Nature Conservation Foundation, 1311, 12th A Main, Vijayanagar 1st Stage, Mysuru 570017, Karnataka, India
3. Work Phone: +91 821 2515601
4. Email address: anand@ncf-india.org 
5. ORCID: https://orcid.org/0000-0001-7094-1314

CONTACT #4
1. Name: T. R. Shankar Raman 
2. Work Address: Nature Conservation Foundation, 1311, 12th A Main, Vijayanagar 1st Stage, Mysuru 570017, Karnataka, India
3. Work Phone: +91 821 2515601
4. Email address: trsr@ncf-india.org 
5. ORCID: https://orcid.org/0000-0002-1347-3953

Keywords: tropical rainforest, plantations, Anamalai Hills, animal roadkill, linear infrastructure intrusions, highways, road ecology, animal-vehicle collisions  

Geographic Coverage:
1. Location/Study Area: Valparai Plateau, Tamil Nadu, India; Anamalai Tiger Reserve, Tamil Nadu, India
2. GPS coordinates: Valparai Plateau (10°15'- 10°22'N, 76°52' - 76°59'E); Anamalai Tiger Reserve (10°12' - 10°35'N, 76°49' - 77°24'E)

Temporal Coverage:
1. Begins: 2011-06-01 (Year, Month, Day)
2. Ends: 2013-05-31 (Year, Month, Day)

Methods:
Methods involved repeated surveys along the road routes searching for roadkills and habitat sampling as described in Jeganathan et al. (2018), Current Science 114(3): 619-626, DOI: 10.18520/cs/v114/i03/619-626

Files included:
Besides this 00_README.txt file, the dataset includes the following six files as explained below:
1) 01_habitat_length.csv -- details of road routes surveyed as line transects
2) 02_sampling_events.csv -- details of individual line transect sample surveys along road routes
3) 03_roadkill_data_final.csv  -- roadkill occurrence data from sample surveys along road routes
4) 04_canopy_and_habitat.csv -- canopy and habitat readings along road routes (transects) surveyed
5) 05_roadkill_transects_all.kml -- KML file containing geographic tracks of 11 road routes surveyed as roadkill transects
6) 06_road_transects_map.jpg -- Map of surveyed routes corresponding to Figure 1 in Jeganathan et al. (2018) 

01_habitat_length.csv
transect: name of road route surveyed as a line transect
route_description: description of road route
tlength_km: transect length along road in kilometres (km)
tlength_m: transect length along road in metres (m)
forest: extent of the road in metres (m) with forest on both sides
forest_tea: extent of the road in metres (m) with forest on one side, tea on the other
coffee_forest: extent of the road in metres (m) with forest on one side, coffee plantation on the other
tea: extent of the road in metres (m) with tea plantation on both sides
coffee: extent of the road in metres (m) with coffee plantation on both sides
eucalyptus: extent of the road in metres (m) with eucalyptus plantation on both sides
eucalyptus_tea: extent of the road in metres (m) with eucalyptus on one side, tea plantation on the other

02_sampling_events.csv
season: monsoon (June to December 2011) or summer (March to June 2012 prior to the onset of 2012 monsoon)
transect: name of road route surveyed as a line transect
transect: name of road route surveyed as a line transect
tcode: unique code for each individual survey of a road route (transect) coevered on a specific date
eventDate: date of road survey
tlength: transect length along road in kilometres (km)

03_roadkilldata_final.csv
sno: serial number of observation
season: monsoon (June to December 2011) or summer (March to June 2012 prior to the onset of 2012 monsoon)
transect: name of road route surveyed as a line transect
tcode: unique code for each individual survey of a road route (transect) coevered on a specific date
eventDate: date of road survey
fielddate: date of road survey as initially noted (for two surveys completed over two successive days, the initial date was recorded as eventDate for 2011-06-17 = 2011-06-16 and eventDate for 2011-07-06 = 2011-07-05
tlength: transect length along road in kilometres (km)
verbatimIdentification: original identification of roadkilled taxon 
vernacularName: common name of taxon
scientificName: scientific name of taxon for corresponding taxonomic level of identification 
taxonRank: rank of taxon indicating for corresponding taxonomic level of identification
taxonRemarks: category of taxon as noted for analysis
verbatimCoordinateSystem: coordinate system used for initial data collection
verbatimSRS: SRS of the location data collected (EPSG:32643/WGS84)
georeferenceRemarks: note indicating locations were converted from UTM (zone 43 N) to latitude longitude using QGIS software
verbatimLongitude: UTM longitude (Easting) as originally recorded
verbatimLatitude: UTM latitude (Northing) as originally recorded
decimalLongitude: longitude in decimal degree East
decimalLatitude: latitude in decimal degrees North
habitat: habitat on either side of the road (forest - forest on both sides; forest_tea - forest on one side, tea on the other; human - human settlements; coffee - coffee plantation on both sides; coffee_forest - coffee on one side, forest on the other; eucalyptus - eucalyptus plantation on both sides; eucalyptus_tea - eucalyptus on one side, tea on the other; tea - tea plantation)
individualCount: number of individuals recorded as roadkill (0 if no roadkills in that survey)
occurrenceStatus: indicated as 'present' for roadkills, or 'absent' if no roadkills recorded 
occurrenceRemarks: notes and remarks if any

04_canopy_and_habitat.csv
transect: name of road route surveyed as a line transect
verbatimroute: route name as originally noted
sno: serial number
canopycover: 0 if tree canopy absent, 1 if tree canopy present above point of observation
canopyoverlap: horizontal overlap of tree canopy above point of observation ranked as 0 - no canopy above; 1 canopy present but barely touching or overrlapping; 2 - canopy overlapping with sky still visible through leaves; 3 - canopy overlaps overhead densely with sky scarcely visible
verticaloverlap: vertical gap between canopy or branches of trees above point of observation ranked as 0 - very wide; 1 - barely touching, 2 - significant vertical overlap, 3 - substantial and dense vertical overlap
habcode: two letter alphabetical code with each letter indicating habitat on one side of the road at the point of observation with f - forest, t - tea, c - coffee, e - eucalyptus, v - village or human habitation, m - dam or reservoir
habno: numeric category for habitat on either side coded as 1 for monocultures (ee, tt); 2 for mixed forest and plantation (ef, ft, etc.); 3 for forest (ff), and 4 for coffee plantation (cc) 
longitude: longitude in decimal degrees east 
latitude: latitude in decimal degrees north

05_roadkill_transects_all.kml
This KML file contains all 11 road routes surveyed as roadkill transects.

06_road_transects_map.jpg
This map illustrating the surveyed road routes corresponds to Figure 1 in Jeganathan et al. (2018), Current Science 114(3): 619-626, DOI: 10.18520/cs/v114/i03/619-626
