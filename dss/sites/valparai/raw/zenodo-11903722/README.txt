This dataset contains Mammal occurrence records (January 2020 - June 2023) in the Valparai Plateau and Anamalai Tiger Reserve, Western Ghats, India. It includes a few occurrence records of reptiles. Occurrence records were gathered in the field by researchers of the Nature Conservation Foundation, India, using a mobile data collection application. Suggested citation is:
Nature Conservation Foundation (2024). Mammal occurrence records (2020-23) in the Valparai Plateau and Anamalai Tiger Reserve, Western Ghats, India. Nature Conservation Foundation, India. Dataset, Zenodo. DOI: 10.5281/zenodo.11903722
 
CONTACT #1
1. Name: T. R. Shankar Raman 
2. Work Address: Nature Conservation Foundation, 1311, 12th A Main, Vijayanagar 1st Stage, Mysuru 570017, Karnataka, India
3. Work Phone: +91 821 2515601
4. Email address: trsr@ncf-india.org 
5. ORCID: https://orcid.org/0000-0002-1347-3953

CONTACT #2
1. Name: Divya Mudappa 
2. Work Address: Nature Conservation Foundation, 1311, 12th A Main, Vijayanagar 1st Stage, Mysuru 570017, Karnataka, India
3. Work Phone: +91 821 2515601
4. Email address: divya@ncf-india.org 
5. ORCID: https://orcid.org/0000-0001-9708-4826

Keywords: tropical rainforest, plantations, Anamalai Hills, Western Ghats, animal distribution, mammals 


Geographic Coverage:
1. Location/Study Area: Valparai Plateau, Tamil Nadu, India; Anamalai Tiger Reserve, Tamil Nadu, India
2. GPS coordinates: Valparai Plateau (10°15'- 10°22'N, 76°52' - 76°59'E); Anamalai Tiger Reserve (10°12' - 10°35'N, 76°49' - 77°24'E)

Temporal Coverage:
1. Begins: 2020-01-11 (Year, Month, Day)
2. Ends: 2023-06-02 (Year, Month, Day)

Besides the 000_readMe.txt file containing this information, the dataset includes 60 images (photographs), three comma-delimited text (csv) files, and one R markdown text file with R code as explained below:
1) 001_mammalData.csv -- This file has the main mammal occurrence data with relevant and renamed columns derived from the original downloaded Excel worksheet file

2) 002_placeLocs.csv  -- This file lists names places for which the GPS location was unavailable from the mobile phone application, and was manually assigned to coordinates with 500 m accuracy

3) 003_nameMatch.csv -- This file matches the name as originally recorded with the correct common name and scientific name

4) 004_mammup.Rmd -- R code for processing the files to create a file for upload as an occurrence dataset on the Global Biodiversity Information Facility (GBIF.org)

+60 image files (with ".jpg" file extension)

FILES INCLUDED IN DATASET

001_mammdata.csv
This file has the main mammal occurrence data with relevant and renamed columns derived from the original downloaded Excel worksheet file 
recordedBy: Observer who recorded/made the observation
username: Username of person on whose mobile phone the data were noted
timestamp: Automatic time stamp of date and time when app was used
date: Date of observation
time: Time of observation
decimalLatitude: Latitude in decimal degrees N
decimalLongitude: Longitude in decimal degrees E
GPSaltitude: Altitude in metres
GPSaccuracy: Horizontal accuracy of GPS location in metres
place: Name of locality
habitat: Habitat type
species: Species common name
count: Number of individuals observed
countType: Total (solitary or fully counted groups) or Partial (incompletely counted groups)
obsType: Type of observation: sighting, sign (droppings or vocalisation), death, roadkill, electrocution, other
notes: Notes or remarks on observation
imageID: Image filename if available (NA, if not available)
instanceID: Automatically generated identifier of observation

002_placeLocs.csv
This file lists names places for which the GPS location was unavailable from the mobile phone application, and was manually assigned to coordinates with 500 m accuracy
place: Name of locality as recorded
lat: Assigned latitude in decimal degrees N
long: Assigned longitude in decimal degrees E
GPSaccuracy: Assigned as 500 m – Horizontal accuracy of GPS location in metres

003_nameMatch.csv
This file matches the name as originally recorded with the correct common name and scientific name.
verbatimIdentification: Identification as originally recorded in the ‘species’ column of the mammdata.csv file
vernacularName: Common or engish name
scientificName: Scientific name

004_mammup.Rmd
R code for processing the files to create a file for upload as an occurrence dataset on the Global Biodiversity Information Facility (GBIF.org)
