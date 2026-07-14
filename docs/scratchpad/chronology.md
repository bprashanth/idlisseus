# Chronological experiments on the dgx

## Phase 1: testing models 

The first phase began with testing various models. At this point, my goal was simply to give everyone on the team a model - a chatgpt - of their own. Having just read about antirez's ds4, I was excited to try it. My first plan was to deploy a openweb ui frontend and point it at ds4. But i found odeysseus, a similar framework that allowed multi user login without much fiddling. I liked it because it allowed a comparison of answers across different models and had a simple built in agent. 

So this brings us to the first benchmark. 
1. Hermes vs odeysseus agent
2. seed oss vs ds4 vs qwen

What i did was ask all of them a sufficiently complicated wildfire related search and summarize task. Hermes planned better and had a built in database that was auditable, the idlisseus loop was quicker because it did; search -> decide -> search -> decide.. stop at max turns. Vs hermes, which did search, serach, search, search -> summarize -> evalute. 

Eitherways, no matter what harness and model I used, i realized that the roadblock was seraching and finding the right papers. This can be split up into 3 subproblems: 

1. The engine: Google serach itself would block, but searXNG was good. 
2. The connection: every time the agent had to rediscovery tricks around the apis, ssl bypass, login. This would take time and trial and error. 

3. The results it found were very contxt / whimsy dependent. Sometimes it would result in a higher quality summary based on the first 3 docs, sometimes it would spiral on a ssl failure. 

## Phase 2: testing retrieval 

This made is adequately clear that we should not be wasting turns and tokens on rebuilding connectors to well known data sites from scratch everytime. Nor should we rely on the fickleness of search. Instead we should 
1. Have a set of connectors for well known data sources
2. Cache known hits 
3. Index known hits
4. Fetch on demand and recache and index 
5. Search both the index andd the internet on queries 

The question of translating a user request -> a set of lookup datasets -> a visulization shifted to user request -> choose known connectors -> do a pass through cache serach -> visualize user request. 

Having overcome the serach bottleneck, two things started to become clear. 
1. We need some kind of semantic lookup to help map terms like invasives to weeds or lantana.
2. We need to integrate map layers for ecological usefulness over and above simple angitgravity style scatter search. 

## Phase 3: Self improvement 

With some structure around this idea of connectors emerging naturally, the idea of eaerth engine/bhuvan/isro/worldclim... dataset connectors was easy to arrive at. 

However, while evaluating 1 it started to get clearer that the first problem wasn't so much search anymore. Having fixed connectors and some basic search mechanism - i.e. to the point where at least a finite working set of datastes were retrieved for a test question like wildfires - it was beomcing clear that we would need some way to self improve. How else would we be able to discover new connectors and datasets? 

This had 3 parts
1. Use an agnet to set a "syllabus" - some 10 questions on a topic, say wildfires
2. Come up with a way to score the answers to this question: did it pull the right data sources (ask the agent itself to list a set of ideal data sources, then run the question through hermes -> ds4 and see if it pulls them), did it model the right answers, did it find points and papers etc. 
3. For all those with bad scores, mine the hermes db traces to understand why: was the connnector missing, did it fail to call the connector, was there inadequate data.
4. For those that had inadequate data, run a scout to look for new papers 
5. For new sources of papers that are found and need api keys, flag for user review 

This increased the corpus of papers from 17 -> 169 -> 256

### Phase 4: Data cards and retrieval (semantic retrieval) 

Till now, the number of papers was small enough and the questions being asked were easy enough that simple keyword search sufficed but as the number of papers grew i found i needed true semantic serach. I needed to translate words like snake to cobra for example. While this is what a classical llm does, what i also needed was to find variables within datasets of papeers that had unrelated titles (eg wildfire in abstract but variable  has invasive presence information). To do this, i found i had to ingest the codebook itself into a semantic db. 

At this point i ran a 3 way experiment: 
1. Plain text search over data cards 
2. LLM over all data cards 
3. Embeddings and data cards 

Embedding search won. 
So now we had overcome: a. organic growth of corpus and syllabus b. finding semantically what the user wanted over the growing corpus. However the problem of interpreting that found data into insights still remained. how do you go from "i have found 10 datasets" to "here is a meaningful and verifiable interpretation of the synthesis of those 10 datasets"?

### Phase 5: Algebra

So at this point we had the following:
input search -> 
1. A variety of paper data sources 
2. A set of maps 
3. Some models to run across those points and maps 

The problem became when to run the models?

for example we could say "help me visualize lantana" but what does that mean in a given landscape? 
a. Help me visualize the points? 
b. What if there are no points - just say so? we can do better 
    - visualize them from adjacent squares that have similar climate (sdm)
    - visualize them from adjacent squares that have similar overall satellite layers (random forest) 

And what's more, a few realistic questions didn't stop at "help me visualize", they went on to say: is this plot improving? is plot a better than plot b? is lantan around elephants? 

While one way to address these questions is to rathole on the definition of better or around, we chose instead to offer a best approximation of the answer while pointing out the limitations and asking for clarification. For example, are lantana arond elephants is a relational algebra question, more generally: is x around y. Is this plot improving is too: aggregate greenness over plot, compare with aggregate greenenss over plot at t2, fit to a line with slope. Rather than make up an answer, we used the llm to synthezie the set of algebra operations, then used the algebra to examine the truth in the data. 

We found that while it's impossible to model the landscape with algebra, it is possible to model questions humans can ask abouut the landscape with algebra. 

## Phase 6: verification and provenance 

The moment we started introducing more advanced modeling (antigravity did more advanced modeling always it just never really explained what it did) we realized we needed some way to introspect. This led us to two designs: 

1. a `/why` endpoint capable of programatically examining the thinking trace of the last question and breaking down to specific algebra oeprations 
2. A human eyeball verification skill that drew the distribution on a map that can be veerified by a human.

As we did 2 what we found was that humans were only really able to verify higher resolution maps, and that led us to acquire high resolution satellite imagery. 

## Phase 7: models and gates and request data 

As we allowed for deeper verification and comparisons we started to realize that there were really multiple ways to visualize the same data, and showing the right analysis for the right qustion and under the right conditions was important. while we could easily show all three, there were situations in which we should NOT show a specific model output. For example when the climate did not match, or there were not enough points. This led to the concept of gates: if a precondition to running a model to extrapolate points does not exist - dont. 

Simultaneously, we started to explore different models for the same input qustion depending on whether or not conditions were similar / diffeent. This was baked into the gating mechanism, if all models were permissable to answer a question, then it was somewhat easier to verify its authenticity as we could look for an intersection of these models. If not, we needed to flag to the user that we needed more data to run better models. 

## Phase 8: progressive discloser and routing 

At this point it was starting to become clearer that even though we had connectors and tools and embeddings, there was just too much wording in the documents. The prose was  turning into llm whimsy. Even with the algebra rules, it was unable to consistently call for the right tools - it wouldd often forget about papers as a data source reaching instead for a live search on inaturalist, it would forget to ask for clarifications, would somethimes forget to translate local names and scientific names and so on. 

We realized we had to improve the system through 

a. a system of skills: loading tools and context based on progressive discloseure. A structure of the agents markdown so it only loads the required tools at the required times, and can discovery enough about what that tool does via some kind of `--describe` function. 

b. a possible model hierarchy: where we could call on a bigger brain model at strategic points of query processing, to do things that smaller models have demonstrated trouble with. 

This led to another set of questions: where do we deploy the smart model? 

1. Smart at the edges dumb in the middle: if we could make a system like this, it would obviously be best because the grunt tool calling work could be upheld by a cheaper model. 

2. Smart planning: if we could come up with a way that a smart model dictates a plan that could work too. 

Oddly, 2 didn't work out as well. More on this later. 
1 did, but we discovered that between very smart and mid smart (glm52 and 122b qwen) vs just-smart all around (deepseekv4), just-smart all aound won out. 
The thing qwen122b struggled with was pushing back and asking for clarifications. 

## Phase 9: discipline 

There were several aspects of model response that we wanted more disciplined. For example, we wanted 
1. shorter answers that asked questions for clarification instead of making assumptions. 
2. a turn / search / tool cap of x followed by a nudge to summarize efforts till now in 2 remainng turns. 
3. more paralleism in tool calls to wrap up within a timelimit 

Such mechanism, we found, were bbetter placed in hooks or tools, not prose. What we found was that brevity as a mechanism enforced through hooks was more predictable than via md files and a smart model. 

More than that, we discovered that a regression suite massively helped protect discipline. While benchmarks outlined areas for imporvement, regressions protected against loss of discpline while implementing the areas that benchmarks surfaced. 

So an important learning was to model the typical quuestions a place sked for basis data and/or communities and thematic problems surrounding that place. 

