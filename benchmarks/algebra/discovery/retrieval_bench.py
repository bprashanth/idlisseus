"""Retrieval at SCALE (140 cards): keyword vs embeddings vs LLM-over-cards vs hybrid.

v-1 (17 cards) said cards are needed and LLM-over-cards won. The open question this
answers: does that hold at 140 cards, where the one-prompt LLM approach starts to strain
and cryptic column names (slopeSRTM30, densiometer) only decode via the codebook?

Task framing: Varun asks in plain words ("how shady under the canopy"); a study is
RELEVANT if its DATA (columns/codebook) holds the concept (regex signature). Metric:
success@k = did we surface >=1 relevant study in the top k? (Hermes needs one grounded
source, not all of them.) Reported split by literal vs semantic (lay word absent from data).
"""
import json
import os
import re
import subprocess
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CARDS = json.load(open(os.path.join(HERE, "cards.jsonl")))
for i, c in enumerate(CARDS):
    c["id"] = i

# (query as Varun would type it, relevance signature = concept in the study's DATA, kind)
QUERIES = [
    ("how shady is it under the tree canopy", r"densiomet|canopy[_ ]?open|canopy[_ ]?cover|canopy[_ ]?height", "semantic"),
    ("how steep is the hillside", r"slope|srtm", "semantic"),
    ("how acidic is the soil", r"soil[_ ]?ph|\bph\b|acidit", "semantic"),
    ("are frogs breeding in the pools", r"tadpole|euphlyctis|amphib", "semantic"),
    ("weeds taking over the land", r"lantana|prosopis|\binvas", "semantic"),
    ("how much rain falls here", r"rain[_ ]|rainfall", "semantic"),
    ("rotting leaves on the forest floor", r"litter", "semantic"),
    ("how heavy is the wood", r"wood[_. ]?densit|wooddensity", "semantic"),
    ("what do the big cats eat", r"leopard|felid|\bdiet", "semantic"),
    ("when do trees flower and fruit", r"phenolog|flowering|fruiting", "semantic"),
    ("livestock killed by predators", r"depred|livestock", "semantic"),
    # literal controls (the concept word itself appears in the data)
    ("bird species counts", r"\bbird|avifaun", "literal"),
    ("soil pH", r"soil[_ ]?ph|\bph\b", "literal"),
    ("canopy cover", r"canopy", "literal"),
    ("tree girth or diameter", r"\bdbh\b|gbh|diameter|girth", "literal"),
]


def relevant_ids(sig):
    rx = re.compile(sig, re.I)
    return {c["id"] for c in CARDS if rx.search(c["content"])}


def success_at_k(ranked, rel, k):
    return 1 if set(ranked[:k]) & rel else 0


# ---- ARM 1: keyword over card content (title+columns+codebook) ----
STOP = {"the", "and", "for", "how", "are", "does", "here", "under", "over", "taking",
        "much", "what", "when", "they", "them", "with", "into", "is", "it", "on", "or", "do"}


def keyword_rank(query):
    toks = [w for w in re.findall(r"[a-z]{3,}", query.lower()) if w not in STOP]
    scored = [(sum(t in c["content"] for t in toks), c["id"]) for c in CARDS]
    return [i for s, i in sorted(scored, key=lambda x: -x[0]) if s > 0]


# ---- ARM 2: LLM over card summaries (122B chat, no reasoning). One prompt, 140 cards. ----
def llm_rank(query):
    lines = "\n".join(f"{c['id']}: {(c['title'] or '')[:55]} | {', '.join(c['columns'][:10])}"
                      for c in CARDS)
    prompt = (f"Studies (id: title | data columns):\n{lines}\n\n"
              f"A field ecologist asks: \"{query}\". List the ids of studies whose DATA columns "
              f"could answer it (map lay words to columns: shady/canopy=densiometer, steep=slope, "
              f"acidic=pH, frog=tadpole/Euphlyctis, weeds=Lantana/invasive, wood heaviness=wood density). "
              f"Output ONLY a JSON array of ids, most relevant first.")
    body = json.dumps({"model": "qwen", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 200, "temperature": 0,
                       "chat_template_kwargs": {"enable_thinking": False}}).encode()
    for _ in range(3):
        try:
            req = urllib.request.Request("http://172.17.0.1:8001/v1/chat/completions", body,
                                         {"Content-Type": "application/json"})
            txt = json.loads(urllib.request.urlopen(req, timeout=90).read())["choices"][0]["message"]["content"]
            txt = re.sub(r"<think>.*?</think>", "", txt, flags=re.DOTALL)
            m = re.search(r"\[(.*?)\]", txt, re.DOTALL)
            if m:
                nums = [int(x) for x in re.findall(r"\d+", m.group(1))]
                if nums:
                    return nums
        except Exception:
            pass
    return []


# ---- ARM 3: embeddings (bge-small via fastembed, reuse v-1 venv) ----
def embed_rank_factory():
    vp = os.path.join(HERE, "..", "paper_data_v-1", "embvenv", "bin", "python")
    if not os.path.exists(vp):
        return None
    script = os.path.join(HERE, "_emb.py")
    open(script, "w").write(
        "import sys,json,numpy as np\nfrom fastembed import TextEmbedding\n"
        "m=TextEmbedding()\nd=json.load(open(sys.argv[1]))\n"
        "docs=d['docs']\n"
        "de=np.array(list(m.embed(docs)))\n"
        "qe=np.array(list(m.embed(d['queries'])))\n"
        "sims=de@qe.T/(np.linalg.norm(de,axis=1)[:,None]*np.linalg.norm(qe,axis=1)[None,:]+1e-9)\n"
        "print(json.dumps([[int(i) for i in np.argsort(-sims[:,j])] for j in range(sims.shape[1])]))\n")
    # embed the whole card content (includes codebook -> decodes cryptic columns)
    docs = [c["content"][:2000] for c in CARDS]
    queries = [q for q, _, _ in QUERIES]
    payload = os.path.join(HERE, "_emb_in.json")
    json.dump({"docs": docs, "queries": queries}, open(payload, "w"))
    out = subprocess.run([vp, script, payload], capture_output=True, text=True, timeout=300)
    rankings = json.loads(out.stdout.strip().splitlines()[-1])
    return {q: rankings[j] for j, (q, _, _) in enumerate(QUERIES)}


# ---- ARM 4: hybrid = embeddings top-20 pre-filter -> LLM re-rank (the at-scale recipe) ----
def hybrid_rank(query, emb_ranking):
    cand = emb_ranking[query][:20]
    lines = "\n".join(f"{c['id']}: {(c['title'] or '')[:55]} | {', '.join(c['columns'][:10])}"
                      for c in CARDS if c["id"] in cand)
    prompt = (f"Candidate studies (id: title | columns):\n{lines}\n\n"
              f"Ecologist asks: \"{query}\". Which of THESE studies' data could answer it? "
              f"Output ONLY a JSON array of ids, most relevant first.")
    body = json.dumps({"model": "qwen", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 120, "temperature": 0,
                       "chat_template_kwargs": {"enable_thinking": False}}).encode()
    try:
        req = urllib.request.Request("http://172.17.0.1:8001/v1/chat/completions", body,
                                     {"Content-Type": "application/json"})
        txt = json.loads(urllib.request.urlopen(req, timeout=90).read())["choices"][0]["message"]["content"]
        txt = re.sub(r"<think>.*?</think>", "", txt, flags=re.DOTALL)
        m = re.search(r"\[(.*?)\]", txt, re.DOTALL)
        if m:
            nums = [int(x) for x in re.findall(r"\d+", m.group(1))]
            if nums:
                return nums + [i for i in cand if i not in nums]
    except Exception:
        pass
    return cand


def main():
    print(f"corpus: {len(CARDS)} cards\n")
    emb = embed_rank_factory()
    arms = {"keyword": lambda q: keyword_rank(q),
            "LLM(140-1prompt)": lambda q: llm_rank(q)}
    if emb:
        arms["embedding"] = lambda q: emb[q]
        arms["hybrid(emb->LLM)"] = lambda q: hybrid_rank(q, emb)
    K = 3
    agg = {a: {"literal": [], "semantic": []} for a in arms}
    for q, sig, kind in QUERIES:
        rel = relevant_ids(sig)
        print(f"[{kind}] {q!r}  ({len(rel)} relevant studies)")
        for a, fn in arms.items():
            ranked = fn(q)
            s = success_at_k(ranked, rel, K)
            agg[a][kind].append(s)
            top_titles = [CARDS[i]["title"][:32] for i in ranked[:K] if i < len(CARDS)]
            print(f"   {a:18s} hit@{K}={s}  top={top_titles}")
        print()
    print(f"=== success@{K} (fraction of queries with >=1 relevant study in top {K}) ===")
    for a in arms:
        lit = sum(agg[a]["literal"]) / max(1, len(agg[a]["literal"]))
        sem = sum(agg[a]["semantic"]) / max(1, len(agg[a]["semantic"]))
        print(f"  {a:18s} literal={lit:.2f}  semantic={sem:.2f}")


if __name__ == "__main__":
    main()
