# Semantic Data Broker for Conservation 

AIM: can semantic dataset cards help Hermes find the right conservation data at runtime? 

Goals: 
- to see how embedding input datasets on different dimensions (dataset cards) helps with identifying datasets for more complicated semantic conservation based queries 
- to see how different agents/llms producing the same dataset card affects result quality

Non Goals: 
- determine whether hermes can do the final analysis perfectly
- actually ingest all relevant conservation datasets 

## Data buckets 

While it is a non goal to ingest all relevant datasets we first explore the directions the data buckets can take, so we have a good understanding of what data to include in the experiment. 

1. Invasives: lantana, senna, prosopis, chromolaena, cestrum
2. Fire: active fire detections, fuel, seasonality
3. Land cover: forest, grassland, plantation, cropland, scrub, wetlands
4. Restoration/ANR: plots, interventions, survival, recruitment, removal history 
5. Biodiversity: occurrence records, camera traps, acoustic indices, bird/mammal observations 6. Governance: protected areas, reserve boundaries, village/forest administrateive units 
...

some hints on where to find these datasets 
1. Zenodo and ecological experiments in the AOI (south india valparai/gudalur/kotagiri/nilgiris/annamalai region) 
2. NASA FIRMS exposes active fire data APIs
3. ESA world cover provides 10m land cover products 
4. Protected Planet exposes protected-area data through its API
5. Earth engine has various satellite data layers 

In general when it comes to satellite layers, hermes itself can run the earth engine scripts via `earthengine` cli and do the overlapping of layers. The service broker itself can just return a list of possible map dataset layer names.

For the Indian conservation framing, NCF has public material around invasive dispersal networks, Lantana and western ghats restoration. 

So for a user question like: show me where invasives have rebounded post removal around fires - what we would need are: 1. datasets with invasive removal (eg experiments that performed removal) 2. some plan to get fire info. 

Now this can be done at runtime, eg by invoking a different cli (something like the cursor agent cli installed on this machine) and asking it to figure out how to download/achieve the right data on its own. First time it would do this, and cache the embeddings. Second time, even with a different question, it should use the embeddings to find the dataset. 

However, in the near term, we will pre-seed a set of good quality datasets. 

## Pre-seeding data

While the data buckets are broad and general the first benchmark should not be overly complicated, so we can manually debug it and get the experiment to the point where we may replicate it. To start with, we will choose a handful of deterministic sources. 

A1: lantana occurrence records from zenodo and gbif 
A2: fire detection points from NASA FIRMS 
A3: Land cover raster from ESA worldcover
A4: Protected area boundary from Protected planet/WDPA
A5: Restoration plot monitoring data from zenodo 
A6: Invasive removal records from zenodo 
A7: Species observation records from gbif 

We can scope the acquisition of these 7 to a region that's close enough to overlap in queries. You as the claude agent will have to help find these. 

## Benchmark questions

For the first benchmark we will create a gold mapping 

1. Which areas seem most exposed to forest fires near restoration sites? 
Answer: A2 (fire), A5 (restoratoin plots), A3 (land) 
This will require _sombody_ to understand what is a restration site
option a: hermes understands and asks the broker for fire around locations a,b,c
option b: hermes proxies the question, the data layer matches restoration site -> a,b,c

Eitherways we will somehow have to match on location

2. Where should we prioritize lantana removal
Answer: A1 (lantana), A6 (removal), A3(land cover)
This will require _somebody_ to understand that lantana removal pertains to where is lantana today, where has it been removed and when and where is it closest to say a field or plantation

3. Are restored plots showing recovery in native species? 
Answer: A5 (restoration plots), A7(species observation), A9(restoration literature)
Something needs to understand what is a plot, and that we need to compile what is native from a list of observations and literature 

4. Can we compare invasive species records of protected areas against non protected areas? 
Answer: A1 (lantana), A4(protected areas)
This is a straightforward mapping where on the hermes side it can just overlap indices as long as the data returned is for the same rough geographic region - meaning the returned indices should be either something like: here are the boundaries for the protected areas or here's a earth engine or public dataset you can script into to figure this out

5. Is fire risk higher in scrub or plantation areas? 
Answer: A2 (fire), A3(land cover)
Straightforawrd hermes will just have to join up where fire is observed with where land cover is observed. The problem is both these are kind of api calls (fire from FIRMS and landcover from worldcover or earthengine). So the data layer should be able to retrieve the right points basis the aoi. 

Claude you are free to expand these questions based on the datasets we do find, or your undersanding of the goals. But of course you can't have different questions across benchmarks.

## Connectors and Brokering 

As you can see, we need a few different ways to access and think about data 

1. Connectors - these can be directly called by hermes but the data layer should point them out so hermes doesn't go looking all over the place for eg fire data when we have a tried and tested skill. Or maybe they don't need explicit pointing out if they're a skill as hermes might know them directly. 

2. Raw data returns - this is data from eg zenodo or raw zip files the users have ingested that the data layer can return. That is, based on the vector search against each data set at ingestion time, the data layer will just suggest to hermes what data is required, and how to get that data. Of course how to get that data can be understood by heremes too directly via skills. 
In other words, the semantic broker will not be returning points or polygons or anything but just the closest embeddings matching the query. The retrieved records will contain a pointer to the actual data as well as a connector / hints of how to access that data. 

## Core experiment loop

1. Ingest the same 5-10 assets 
2. Generate dataset cards using marker recipe X 
3. index those cards 
4. Run the fixed query set 
5. Retrieve top 5 assets per query
6. Compare retrieved assets against gold expectation
7. Ask Hermes to explain why it chose those assets 
8. Record failure modes 
9. Write experiment report 

It is important to hold the dataset and question set constant while changing markers. 

## Experiment suite 

run these first using: cursor cli (called "agent"), qwen 2.5 coder 14b (or equivalent), qwen 122b. Note that these models are only to index the datasets that have been identified by you (claude) and hermes will still query it via the questions experiment plan. 

You may also comment on whether there will be space to run both 14b and 122b or which will be more valuable as an experiment (if there isn't). 

### Dataset cards 

The idea behind dataset cards are they will be indexed into the vector index (we can just use a file and later go to a db). The recipes below will be used to produce and index these cards and need to be cleaned between experiments.

1. Naive baseline 

Dataset card 
```
title
tags
source
summary
connector
```

eg
```
{
  "name": "fire and disturbance",
  "tags": ["wildfire", "disturbance", "forest risk"],
  "source": "some fire map...",
  "summary": "a map of fire risk disturbances",
  "connector": earthengine
}
```

2. Possible questions 

Add questions this dataset may answer

eg
```
- Where were active fires detected?
- Which month had more fire detections?
- Which land-cover classes overlap with fire points?
```

goal: Does indexing possible questions improve natural-language retrieval?

3. Add conservation tags 

Summary may not capture all attributes of data, eg a data set primarily focused on fire might happen to have lat/lon of lantana too. 

```
invasion pressure
fuel load
fire exposure
restoration outcome
native recruitment
survival
disturbance
edge effect
canopy cover
fragmentation
species presence
management intervention
...
```
These could come from header rows of excel or your internal knowledge of ecology. Include state/site/district and other geotags too. 

Goal: Does ecological vocabulary help the broker retrieve data when the user asks in conservation language?

### Report

The output report should include eg: 
```
Experiment name
Marker recipe
Retrieval score
- all required datasets in top 5 (+1 for each)
- irrelevant rank-1 errors

Question
Retrieval
Reasoning 

Recommended marker changes:...
```
For this to work of course there should be some irrelevant datasets too. 

For example the first experiment could be: 
```
Question:
"Which uploaded datasets can help identify restoration plots exposed to fire risk?"

Expected retrieval:
A5 restoration plot Excel
A2 FIRMS fire detections
A3 land cover

Expected reasoning:
- restoration plots provide intervention locations
- fire detections provide disturbance exposure
- land cover provides habitat/fuel context
- requires spatial join
- cannot infer fire cause
```


## Questions to start with 

1. Is there space for this experiment? 
2. What are the datasets and questions we should include in the suite? 
3. The goal is to understand: a. different models creating same datacards and 2. same model creating different datacards - but what we can do is run the second first, determine the best datacard, then run the first (model compare) against this best datacard. 
4. What connectors do we need to write based on 1 and 2? i guess we can just let hermes call the connectors without having to worry about anything elaborate wrt mcp/api etc. Even the broker can just be a python script that creates the datacard and ingests it in the vector file/db.





