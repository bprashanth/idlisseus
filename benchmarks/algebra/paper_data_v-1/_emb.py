import sys,json,numpy as np
from fastembed import TextEmbedding
m=TextEmbedding()
d=json.load(open(sys.argv[1]))
docs=[c['content'] for c in d['cards']]
de=np.array(list(m.embed(docs)));qe=np.array(list(m.embed([d['query']]))[0])
sims=de@qe/(np.linalg.norm(de,axis=1)*np.linalg.norm(qe)+1e-9)
print(json.dumps([int(i) for i in np.argsort(-sims)]))
