"""Small repeatable retrieval evaluation against the supplied seed gold-set."""
import csv, io, zipfile
from .settings import DATA_ZIP
from .retrieval import retrieve

def evaluate():
    with zipfile.ZipFile(DATA_ZIP) as z:
        raw=z.read('evaluation_questions.csv').decode('utf-8-sig')
    rows=list(csv.reader(io.StringIO(raw)))
    results=[]
    for row in rows:
        if len(row)<5 or row[:5] == ['0','1','2','3','4'] or (row[0].strip().lower() in {'id','eval_id','evaluation_id'}): continue
        eval_id,product,question,expected,topic=row[:5]
        hits=retrieve(question,top_k=3,product_filter=product)
        text=' '.join(x['text'] for x in hits).lower()
        # Topic and expected-answer checks are deliberately transparent baseline metrics.
        expected_terms=[w.lower() for w in expected.split() if len(w)>2]
        matched=sum(1 for w in expected_terms if w in text)
        results.append({'id':eval_id,'product':product,'question':question,'expected':expected,'topic':topic,
          'retrieved':bool(hits),'topic_hit':topic.lower() in text,'expected_term_coverage':round(matched/max(1,len(expected_terms)),2),
          'top_sources':[f"{x['source']}::{x['section']}" for x in hits]})
    n=max(1,len(results))
    return {'count':len(results),'retrieval_hit_rate':round(sum(r['retrieved'] for r in results)/n,3),
      'topic_hit_rate':round(sum(r['topic_hit'] for r in results)/n,3),'results':results,
      'note':'Heuristic seed-set metrics only; expand the gold set to 50–100+ questions and add human relevance judgments before treating this as a quality benchmark.'}

if __name__=='__main__':
    import json; print(json.dumps(evaluate(),indent=2,ensure_ascii=False))
