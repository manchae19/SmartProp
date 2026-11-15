"""Permission-first BM25 + existing E5/FAISS, reciprocal rank fusion and evidence reranking."""
import math
import re
from collections import Counter
from .intent import fold
from .config import RagUnavailable

STOP = set("toi ban minh la co nhung cac cua cho va hay o tai thi nao gi mot duoc ve voi xin biet the nao".split())
def tokens(text):
    return [v for v in re.findall(r"[a-z0-9]+", fold(text)) if v not in STOP]

def bm25(question, documents):
    query=set(tokens(question))
    bags=[Counter(tokens(d['text']+' '+d.get('metadata',{}).get('title',''))) for d in documents]
    lengths=[sum(b.values()) for b in bags];avg=sum(lengths)/max(1,len(bags)) or 1
    frequencies=Counter(word for bag in bags for word in bag)
    scores=[]
    for i,bag in enumerate(bags):
        score=0.0
        for word in query:
            frequency=bag[word]
            if not frequency:continue
            df=frequencies[word]
            idf=math.log(1+(len(bags)-df+0.5)/(df+0.5))
            score+=idf*frequency*2.2/(frequency+1.2*(0.25+0.75*lengths[i]/avg))
        if score:scores.append((i,score))
    return sorted(scores,key=lambda pair:(-pair[1],documents[pair[0]]['sourceId']))

class HybridRetriever:
    def __init__(self,dense):self.dense=dense
    @property
    def embedding(self):return self.dense.embedding
    @property
    def manifest(self):return self.dense.manifest
    def search(self,question,documents,*,internal=False,district=None,categories=None,k=4):
        if not 1<=k<=20:raise ValueError('Invalid retrieval limit')
        eligible=[d for d in documents if d['scope']=='PUBLIC' or internal]
        if district:eligible=[d for d in eligible if d['metadata'].get('district')==district]
        if categories:eligible=[d for d in eligible if d['kind']=='POI_EVIDENCE' and d['metadata'].get('category') in categories]
        if not eligible:return []
        lexical=bm25(question,eligible);by_id={d['sourceId']:d for d in eligible}
        lex_scores={eligible[i]['sourceId']:score for i,score in lexical}
        ranks={};dense_hits=[];dense_ok=True
        for rank,(i,_) in enumerate(lexical[:30],1):ranks[eligible[i]['sourceId']]=1/(60+rank)
        try:
            dense_documents=[d for d in documents if d['scope']=='PUBLIC' or internal]
            dense_hits=self.dense.search(question,dense_documents,internal=internal,district=district,categories=categories,k=min(20,len(eligible)))
        except (RagUnavailable,ImportError):dense_ok=False
        similarities={}
        for rank,d in enumerate(dense_hits,1):
            sid=d['sourceId']
            if sid not in by_id:continue
            similarities[sid]=d.get('similarity',0)
            ranks[sid]=ranks.get(sid,0)+1/(60+rank)
        # For document excerpts require some lexical alignment. A high cosine alone
        # cannot establish that a statute or report answers this particular question.
        ranked=sorted(ranks,key=lambda sid:(-ranks[sid],-lex_scores.get(sid,0),sid))
        result=[];parents={}
        content_query=set(tokens(question))-set('khong chua trong tai lieu thong tin noi dung nay do day'.split())
        for sid in ranked:
            d=by_id[sid];meta=d.get('metadata',{})
            if d['kind']=='SOURCE_DOCUMENT' and (lex_scores.get(sid,0)<=0 or not content_query.intersection(tokens(d['text']+' '+meta.get('title','')))):continue
            parent=meta.get('parentSourceId',sid)
            if parents.get(parent,0)>=2:continue
            parents[parent]=parents.get(parent,0)+1
            result.append({**d,'similarity':similarities.get(sid,0),'lexicalScore':lex_scores.get(sid,0),
                           'hybridScore':ranks[sid],'retrievalMethod':'BM25_E5_RRF' if dense_ok else 'BM25_ONLY_DENSE_UNAVAILABLE'})
            if len(result)>=k:break
        return result
