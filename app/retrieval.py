"""Lightweight local RAG: section-aware chunks + TF-IDF vector retrieval + lexical hybrid fusion + reranking."""
import re, zipfile
from functools import lru_cache
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .settings import DATA_ZIP

@lru_cache(maxsize=1)
def load_chunks():
    chunks=[]
    with zipfile.ZipFile(DATA_ZIP) as z:
        for name in z.namelist():
            if not name.startswith('policy_documents/') or not name.endswith('.txt'): continue
            text=z.read(name).decode('utf-8', errors='replace')
            product=next((line.strip() for line in text.splitlines() if line.strip()), name.split('/')[-1].replace('_',' ').removesuffix('.txt'))
            sections=re.split(r'\n(?=\d+\.\s)', text)
            for sec in sections:
                sec=sec.strip()
                if len(sec)<20: continue
                heading=sec.splitlines()[0].strip()
                chunks.append({'product':product,'source':name.split('/')[-1],'section':heading,'text':sec})
    return chunks

@lru_cache(maxsize=1)
def vector_index():
    chunks=load_chunks()
    vectorizer=TfidfVectorizer(stop_words='english', ngram_range=(1,2), sublinear_tf=True)
    matrix=vectorizer.fit_transform([c['text'] for c in chunks])
    return vectorizer,matrix

def retrieve(question, top_k=5, product_filter=None):
    chunks=load_chunks()
    if not chunks: return []
    vectorizer,matrix=vector_index()
    qv=vectorizer.transform([question])
    semantic=cosine_similarity(qv,matrix).ravel()
    qterms=set(re.findall(r'[a-z0-9]+',question.lower()))
    scores=[]
    for i,c in enumerate(chunks):
        if product_filter and product_filter.lower() not in c['product'].lower(): continue
        terms=set(re.findall(r'[a-z0-9]+',(c['product']+' '+c['section']+' '+c['text']).lower()))
        lexical=len(qterms & terms)/max(1,len(qterms))
        # Hybrid weighted fusion; lexical match can rescue exact policy terms.
        hybrid=0.65*float(semantic[i])+0.35*lexical
        # Simple reranker boosts direct section/topic overlap and product-name mentions.
        section_terms=set(re.findall(r'[a-z0-9]+',c['section'].lower()))
        rerank=hybrid + 0.08*(len(qterms & section_terms)/max(1,len(qterms)))
        scores.append((rerank, hybrid, i))
    scores.sort(reverse=True)
    results=[]
    for rerank,hybrid,i in scores[:top_k]:
        c=chunks[i].copy(); c['score']=round(rerank,4); results.append(c)
    return results
