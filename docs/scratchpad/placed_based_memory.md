# Placed based memory systems 

## Algebra

The technique is called semantic parsing to a closed query algebra. The idea is based on a simple observation: LLMs are unreliable as sources of facts but quite reliable as _compilers_ from English tino a small and constrained formal language. There is an entire literature on this around text-to-SQL. So what we want is: 
1. The model does translation synthesis
2. The algebra does truth

Everything suggested as part of this design follows from taking this stance seriously. 

### Layer 1: The minimum kernel for algebra

| Operation   | Plain meaning                                                    |
| ----------- | ---------------------------------------------------------------- |
| `SELECT`    | Get the relevant observations.                                   |
| `ANNOTATE`  | Add context to each observation.                                 |
| `RELATE`    | Calculate how two sets of things are connected in space or time. |
| `AGGREGATE` | Turn many observations into a pattern, value, map or series.     |
| `COMPARE`   | Measure the difference between two prepared results.             |
| `ESTIMATE`  | Fill an evidence gap using a model.                              |

What about FIT? is it needed for trend? 

### Layer 2: Epistemic

1. ESTIMATES are never run without a GATE check
2. Every node in the tree downstream from a ESTIMATE receives the modelled label
3. VERIFY is a family of operations that equates to 
    - verify-by-eyeball
    - verify-by-agreement
    - verify-by-holdout
    - verify-by-user (ask) 
4. A DataRequest is a first class return type. Every answer evaluates to either: Answered or PartialAnswer + DataRequest. 

## Framework overview 

The framework has a bunch of tools: 
```
find records, search papers, map: (lakes/tree-cover/terrain), "is X near Y", distribution maps (sdm, random forests), fruiting calendars, birds, soil indicators, grazing..
```

The challenge is finding the right set of tools to call for a given query. 

There are two main ways of evaluating progress. First a benchmark: which is a set of questions that scatter usage across all tools. The benchmark models a user with a hidden goal. Simulating a multi turn converstaion, it uses one model to drive the conversation and another (the place based system) to answer. After the benchmark, the supervisor model (the one mimicing the user) runs over the traces checking if properties mentioned in the _constitution_ are upheld by the model during its multiturn conversation. It also checks whether the right tools are called for the right questions, and whether properties like lineage were sustained over the conversation. 

Finding new tools and questions (in other words, increasing the syllabus) is itself a challenge, as is increasing the available datasets to search over. Both these happen through a "scout"- which once again is an agent consulting an llm with the explicity aim of finding things. The technique it applies is simple: look at answers with poor scores and search for answers in that dimension start with papers. In papers, search across authors and linkn to topics. 

As important as finding new papers is finding new questions for the benchmark. 

Once new data sources have been found, the supervisor evaluates (by rerunning the failing questions of the benchmark) whether it can answer questions better. Once again, we mine the traces via a miner process to identify where failures occurred. At this point, assuming the sources are in tact, the failures are reduced to either chaining the wrong tools together or lacking a specific tool. For both cases, we need to be very careful about regressions. 

To prevent regressions, a regression suite is run before modifying the toolset. A small set of must-never-break checks. This is scored as follows: 

1. short - was the answer short and crisp
2. did it use the right connector (question about water -> use the water connector)
3. resolved names to local names (for questions that ask in local names like green snake)
4. papers - for a literature question 
5. transfer-flag - when it modelled did it say so vs pretending its observed
6. clarified - did it ask for clarification with vague requests 


The constitution: this holds the few things that must be true on every answer. Eg: know the place, ask when unsure, be short, be honest (what was observed vs modelled), resolve names, papers-first. It does not hold the how-to for each question. That lives in on-demand recipes. 

The gates: are preconditions that must be true before a model is run. This is so we don't overextend a model across mismatched climates etc. If we can't model, we should say: can't model this, collect this data so we can. 

So the challenge with the constitution is it's expressed as prose, and prose can be ignored by llm whim. The gates on the other hand, are expressed mathamatically (is the climate similar, is the cosine similar across all satellite data similar, do we have enough points) and can't be ignored. 

Hence the way we "enforce" the constitution is through 1. a smarter model, that pushes the user to give clarifications and 2. through hooks that execute during the agentic lifecycle that can examine and enfoce certain properties. For example, if the smart model observes the cheap model doing things that don't correlate to tool call outputs, it cuts it off. And this "cutoff" would affet the benchmark scoring, which would result in fixing or tweaking of the tools or prompts. 


## Jailbreaks 

The first and foremost reason is this: prose is a suggestion. And the vaguer the prose is, the more of a suggestion it becomes. 

1. Run a `pre_llm_call` to clarify vague queries. This will send the query standalone to a model endpoint, and the endpoint will just judge whether that query is vague or specific. If vague, it will ask for clarity. This prevents overly broad queries.

2. Run a `pre_tool_call` that nudges the llm to be quick and crisp. 

