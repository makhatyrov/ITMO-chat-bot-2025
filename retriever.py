# Very small BM25-like retriever over our JSON/texts
import math, re, json
from pathlib import Path

DATA = Path(__file__).parent / "data"
DOCS = []

for p in DATA.glob("*.json"):
    blob = json.load(open(p, encoding="utf-8"))
    if "programs" in blob:
        for prog in blob["programs"]:
            DOCS.append({"id": prog["slug"], "text": " ".join([prog.get("title","")," ".join(prog.get("notes",[]))," ".join(prog.get("faq",[]))])})
    else:
        DOCS.append({"id": p.stem, "text": json.dumps(blob, ensure_ascii=False)})

def tokenize(s):
    return re.findall(r"[а-яa-z0-9]{2,}", s.lower())

def build_index(docs):
    N = len(docs)
    df = {}
    tok_docs = []
    for d in docs:
        toks = tokenize(d["text"])
        tok_docs.append(toks)
        for t in set(toks):
            df[t] = df.get(t,0)+1
    return {"N":N,"df":df,"docs":docs,"tok_docs":tok_docs}

INDEX = build_index(DOCS)

def score(query, idx=INDEX, k1=1.6, b=0.75):
    q = tokenize(query)
    scores = [0.0]*len(idx["docs"])
    avgdl = sum(len(t) for t in idx["tok_docs"])/max(1,len(idx["tok_docs"]))
    for qi in q:
        n = idx["df"].get(qi,0)
        if n==0: 
            continue
        idf = math.log((idx["N"] - n + 0.5)/(n + 0.5) + 1)
        for i, toks in enumerate(idx["tok_docs"]):
            freq = toks.count(qi)
            if freq==0: continue
            dl = len(toks)
            s = idf * (freq*(k1+1))/(freq + k1*(1 - b + b*dl/avgdl))
            scores[i]+=s
    ranking = sorted(enumerate(scores), key=lambda x:x[1], reverse=True)
    return [(idx["docs"][i]["id"], sc) for i,sc in ranking if sc>0]

def search(query, topk=5):
    return score(query)[:topk]

if __name__=="__main__":
    print(search("стоимость обучения и формат занятий"))
