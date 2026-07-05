"""Card-retrieval benchmark: keyword vs LLM-over-cards vs embeddings.

The question (from semantic_broker): when a query says 'invasive' but the column says
'Prosopis' (or 'acidity'->pH, 'frog'->Euphlyctis, 'steepness'->slope), which retrieval
method surfaces the right study's card? Metric: Recall@k over hand-labelled relevant cards.
Decides — empirically, at our scale — whether keyword+LLM suffices or embeddings are needed.
"""
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CARDS = json.load(open(os.path.join(HERE, "cards.jsonl")))
for i, c in enumerate(CARDS):
    c["id"] = i

# query -> (relevant card-title substrings, kind). Relevant = the study's DATA holds the concept.
QUERIES = [
    # literal controls (concept word appears in card)
    ("soil pH", ["Soil properties of degraded", "Cashew orchard soil", "Soil properties of evergreen"], "literal"),
    ("mammal occurrence", ["Mammal occurrence"], "literal"),
    ("canopy", ["Birds and Vegetation of Shade Coffee"], "literal"),
    # GENUINE semantic gaps: query shares NO word with the card's columns/species
    ("how steep are the hillsides", ["Varying impacts of logging"], "semantic"),          # -> slope
    ("acidity levels in the ground", ["Soil properties of degraded", "Cashew orchard soil", "Soil properties of evergreen"], "semantic"),  # -> pH
    ("heaviness or density of timber", ["Wood density for 26 plant"], "semantic"),        # -> wood density
    ("froglets breeding in pools", ["Abiotic and biotic drivers on tadpoles"], "semantic"),  # -> Euphlyctis/tadpole
    ("what does the big spotted feline eat", ["Prey abundance and leopard diet"], "semantic"),  # -> leopard
    ("shadiness under the trees", ["Birds and Vegetation of Shade Coffee"], "semantic"),  # -> densiometer/canopy openness
    ("rotting plant matter on the ground", ["Birds and Vegetation of Shade Coffee"], "semantic"),  # -> leaflitter
]


def _relevant_ids(subs):
    return {c["id"] for c in CARDS if any(s.lower() in c["title"].lower() for s in subs)}


def recall_at_k(ranked_ids, relevant, k):
    if not relevant:
        return None
    return len(set(ranked_ids[:k]) & relevant) / len(relevant)


# ---- ARM 1: keyword ----
def keyword_rank(query):
    toks = [w for w in re.findall(r"[a-z]{3,}", query.lower()) if w not in
            ("the", "and", "for", "how", "are", "any", "their", "data", "values", "floor")]
    scored = [(sum(t in c["content"] for t in toks), c["id"]) for c in CARDS]
    return [i for s, i in sorted(scored, key=lambda x: -x[0]) if s > 0]


# ---- ARM 2: LLM over all cards (122B completions, no reasoning) ----
def llm_rank(query):
    cards = "\n".join(f"{c['id']}: {c['title'][:60]} | cols: {', '.join(c['columns'][:12])}"
                      for c in CARDS)
    prompt = (f"Cards (a study each, with data columns):\n{cards}\n\n"
              f"Query: \"{query}\". List the card numbers whose DATA could answer it "
              f"(map synonyms: acidity=pH, frog=Euphlyctis, steepness=slope, cattle=gaur). "
              f"Output ONLY a JSON array of card numbers, most relevant first.")
    # chat endpoint + enable_thinking:false -> fast, no reasoning block eating the budget.
    body = json.dumps({"model": "qwen", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 150, "temperature": 0,
                       "chat_template_kwargs": {"enable_thinking": False}}).encode()
    for _ in range(3):
        try:
            req = urllib.request.Request("http://172.17.0.1:8001/v1/chat/completions", body,
                                         {"Content-Type": "application/json"})
            txt = json.loads(urllib.request.urlopen(req, timeout=60).read())["choices"][0]["message"]["content"]
            txt = re.sub(r"<think>.*?</think>", "", txt, flags=re.DOTALL)
            m = re.search(r"\[(.*?)\]", txt, re.DOTALL)   # any bracket; tolerate quotes/prose
            if m:
                nums = [int(x) for x in re.findall(r"\d+", m.group(1))]
                if nums:
                    return nums, None
        except Exception as e:
            last = f"err:{e}"
    return [], locals().get("last", "no-json")


# ---- ARM 3: embeddings ----
def embed_rank_factory():
    vp = os.path.join(HERE, "embvenv", "bin", "python")
    if not os.path.exists(vp):
        return None
    import subprocess
    script = os.path.join(HERE, "_emb.py")
    open(script, "w").write(
        "import sys,json,numpy as np\nfrom fastembed import TextEmbedding\n"
        "m=TextEmbedding()\nd=json.load(open(sys.argv[1]))\n"
        "docs=[c['content'] for c in d['cards']]\n"
        "de=np.array(list(m.embed(docs)));qe=np.array(list(m.embed([d['query']]))[0])\n"
        "sims=de@qe/(np.linalg.norm(de,axis=1)*np.linalg.norm(qe)+1e-9)\n"
        "print(json.dumps([int(i) for i in np.argsort(-sims)]))\n")

    def rank(query):
        payload = os.path.join(HERE, "_emb_in.json")
        json.dump({"query": query, "cards": CARDS}, open(payload, "w"))
        try:
            out = subprocess.run([vp, script, payload], capture_output=True, text=True, timeout=120)
            return json.loads(out.stdout.strip().splitlines()[-1])
        except Exception:
            return []
    return rank


def main():
    embed_rank = embed_rank_factory()
    arms = {"keyword": keyword_rank, "LLM(122B)": lambda q: llm_rank(q)[0]}
    if embed_rank:
        arms["embedding"] = embed_rank
    K = 3
    agg = {a: {"literal": [], "semantic": []} for a in arms}
    for q, subs, kind in QUERIES:
        rel = _relevant_ids(subs)
        print(f"\n[{kind}] {q!r}  (relevant cards: {sorted(rel)})")
        for a, fn in arms.items():
            ranked = fn(q)
            r = recall_at_k(ranked, rel, K)
            agg[a][kind].append(r if r is not None else 0)
            print(f"   {a:12s} recall@{K}={r:.2f}  top{K}={ranked[:K]}")
    print(f"\n=== mean Recall@{K} ===")
    for a in arms:
        lit = sum(agg[a]["literal"]) / max(1, len(agg[a]["literal"]))
        sem = sum(agg[a]["semantic"]) / max(1, len(agg[a]["semantic"]))
        print(f"  {a:12s} literal={lit:.2f}  semantic={sem:.2f}")
    print("\nRead: if keyword semantic << LLM/embedding semantic -> semantic retrieval needed. "
          "If LLM≈embedding and corpus small -> LLM-over-cards is enough (no embeddings yet).")


if __name__ == "__main__":
    main()
