This dataset includes the complete data download and summaries of weather data from the weather station at Iyerpadi, Valparai Plateau, Anamalai Hills, India. 

DATASET CONTACT
1. Name: T. R. Shankar Raman 
2. Work Address: Nature Conservation Foundation, 1311, 12th A Main, Vijayanagar 1st Stage, Mysuru 570017, Karnataka, India
3. Work Phone: +91 821 2515601
4. Email address: trsr@ncf-india.org 
5. ORCID: https://orcid.org/0000-0002-1347-3953

Keywords: Climate, weather data, air temperature, atmospheric precipitation, rainfall, atmospheric humidity, photosynthetically active radiation, wind speed, wind direction, dew point,  tropical rainforest, seasonality, phenology


##Iyerpadi Weather Stathttps://osf.io/f83vu/overviewion, Valparai, Tamil Nadu, India

Weather Station Make and Model
HOBO U30 Station (NRC - No remote connection)
(HOBO® Data Loggers, a LI-COR® Brand)
Manual: https://www.onsetcomp.com/sites/default/files/resources-documents/11866-M U30-NRC Manual.pdf
Logger Serial Number: 10243750

Weather Station Location:
10.363725° N, 76.977628° E

Weather Station Elevation:
1234 m above mean sea level

Weather Logger frequency:
From start to 2020-06-17: 4 samples per hour, at mins = (6, 21, 36, 51) OR (14, 29, 44, 59)
After 2020-06-17: 2 samples per hour, at mins = (15, 45) OR (0, 30 )

Temporal Coverage:
Start: 23 January 2014
End: 31 January 2026

Spatial Coverage:
Around Iyerpadi (10.363725° N, 76.977628° E), Valparai Plateau, Tamil Nadu, India


##Weather datasets, code, and summaries

01_Iyerpadi_Weather_Data.csv
Compiled raw data as downloaded from the Iyerpadi Weather Station, Valparai Plateau, Tamil Nadu, India, with the following columns (serial number of sensors in parantheses)
sno	Serial Number
date	Date
time	Time of record (GMT+05:30)
windDirection	theta, ø (LGR S/N: 10243750, SEN S/N: 10214844)
PAR	Photosynthetically Active Radiation, PAR, µmol/m²/s (LGR S/N: 10243750, SEN S/N: 10219879)
rain	Rainfall in mm (SEN S/N: 10227819)
voltage	Volts, V (SEN S/N: 10233271)
current	Current, mA (SEN S/N: 10233271)
temp	Temperature °C (SEN S/N: 22116632)
RH	Relative Humidity, RH % (SEN S/N: 22116632)
windSpeed	Wind Speed, m/s (SEN S/N: 20310292)
gustSpeed	Gust Speed, m/s (SEN S/N: 20310292)
DewPt	Dew Point, °C (SEN S/N: 22116632)
BattV	Battery voltage, V

02_parry2018rain.csv
Rainfall data from 31 January 2018 to 30 June 2018 at Iyerpadi sourced from rain guage measurements by Parry Agro Industries Ltd.
Date	Date of record
Rain_cm	Rainfall in cm
Rain_mm	Rainfall in mm

03_IyerpadiDailyFull3.0.csv
Complete daily dataset from 2014-01-24 to 2026-01-31 with average daily values of climate variables after filling gaps in the raw dataset (01_Iyerpadi_Weather_Data.csv) using the 7-day running mean (calculated from across years) of the corresponding variable centred on the missing date. See R code (05_iyweather3.0.Rmd) for analytical code. Variable names should be self-explanatory as the variables and units correspond to the main variables in the raw dataset for Temperature, Rainfall, RH, Wind Speed, Gust Speed, and Dew Point, presented here as the daily mean, minimum (prefix min) and maximum (prefix max) of the corresponding variables. In addition, please note:
radiance	Average daily value of PAR (Photosynthetically Active Radiation, PAR, µmol/m²/s)
daylight	The number of daylight hours calculated as hours with photosynthetically active radiation (PAR > 1.2 μmol m–² s–¹)

04_IyerpadiMonthlySummary3.0.csv
Monthly averages of climate variables based on the complete daily dataset (03_IyerpadiDailyFull3.0.csv) derived using R code (05_iyweather3.0.Rmd). Variables as in the complete daily dataset file as explained above.

05_iyweather3.0.Rmd
R code for analysis of weather data and preparation of complete daily data and monthly summary datasheets: 03_IyerpadiDailyFull3.0.csv (and) 04_IyerpadiMonthlySummary3.0.csv

Fig1_MissingValues.jpg
Figure displaying missing values in the data due to temporary sensor failure, battery problems, or other malfunctions in Iyerpadi Weather Station, Valparai Plateau, Tamil Nadu, India.

Fig2a_ombrograph.jpg
Ombrothermic diagram or Walter-Leith Diagram showing monthly temperature (primary y-axis) and rainfall in mm (secondary y-axis) based on average across years (2014-2025): data from Iyerpadi Weather Station, Valparai Plateau, Tamil Nadu, India.

Fig2b_climvars.jpg
Graph depicting annual pattern of four climate variables (lines: loess fit of daily means at span = 0.4;  points: daily means; grey shaded area: ±1 SE of daily mean) based on data from Iyerpadi Weather Station, Valparai Plateau, Tamil Nadu, India.

Fig3_LongTermPatterns.jpg
Graphs depicting inter-annual variation and patterns in rainfall, temperature, and PAR radiance from 2o14 to 2025 based on data from Iyerpadi Weather Station, Valparai Plateau, Tamil Nadu, India.


## Annexures

Xtra_11866-M U30-NRC Manual.pdf
HOBO® U30 USB Station (U30-NRC) Manual

Xtra_Post installation inventory.pdf
Inventory of HOBO® U30 weather station equipment after installation




