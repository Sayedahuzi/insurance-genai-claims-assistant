"""Question router and grounded answer composer. Optional OpenAI-compatible LLM; local mode always works."""
import os, re, json, urllib.request
from .tools import extract_id, claim_summary, claim_details, policy_lookup, customer_lookup, hospital_lookup
from .retrieval import retrieve
from .settings import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

POLICY_NAMES=['Health Secure Plus','Family Care Gold','Maternity Protect','Senior Health Shield','Global Travel Secure','Critical Care Elite','Two Wheeler Secure','Car Shield Plus','Motor Protect Comprehensive','Student Travel Protect']

def detect_product(question):
    q=question.lower()
    return next((p for p in POLICY_NAMES if p.lower() in q),None)

def route_question(q):
    lower=q.lower()
    if extract_id(q,'CLM'):
        if any(w in lower for w in ['analy','summary','summari','missing document','document','pending why','why is my claim','why claim']): return 'claim_analysis'
        return 'claim_sql'
    if extract_id(q,'POL'): return 'policy_sql'
    if extract_id(q,'CUST'): return 'customer_sql'
    if extract_id(q,'HOSP') or 'hospital' in lower and any(w in lower for w in ['network','empanel','provider','status']): return 'hospital_sql'
    if any(w in lower for w in ['interaction history','customer interaction','sentiment','support channel']): return 'interaction_sql'
    if any(w in lower for w in ['policy','covered','coverage','waiting period','exclusion','maternity','pre-existing','reimbursement','cashless','deductible','co-pay','copay','claim procedure','dental','newborn']): return 'policy_rag'
    return 'hybrid_or_clarify'

def _fmt(value): return 'Not recorded' if value in (None,'','nan','NaN') else str(value)

def _claim_answer(cid, analysis=False):
    result=claim_summary(cid) if analysis else None
    c=result['claim'] if result else claim_details(cid) if not analysis else None
    if not c: return f'I could not find claim {cid} in the structured claims table. Please verify the claim ID.', [], 'claims SQL'
    parts=[f"**Claim {c['claim_id']}**",f"- Status: {_fmt(c.get('claim_status'))}",f"- Claim date: {_fmt(c.get('claim_date'))}",f"- Claim amount: ₹{_fmt(c.get('claim_amount'))}",f"- Approved amount: ₹{_fmt(c.get('approved_amount'))}",f"- Policy: {_fmt(c.get('product_name'))} ({_fmt(c.get('policy_id'))})",f"- Diagnosis/loss: {_fmt(c.get('diagnosis_or_loss_type'))}",f"- Hospital: {_fmt(c.get('hospital_name'))}; network status: {_fmt(c.get('network_status'))}",f"- Manual review flag: {_fmt(c.get('manual_review_flag'))}"]
    if c.get('rejection_or_adjustment_reason'): parts.append(f"- Rejection/adjustment reason recorded: {_fmt(c.get('rejection_or_adjustment_reason'))}")
    sources=['claims + policies + customers + hospitals SQL']
    if analysis:
        def names(items): return ', '.join(d['document_type'] for d in items) or 'None found in document table'
        parts += ['', '**Claim document check**',f"- Missing: {names(result['missing_documents'])}",f"- Uploaded but not verified: {names(result['pending_documents'])}",f"- Rejected: {names(result['rejected_documents'])}"]
        if result['recent_interactions']:
            parts.append('- Recent interactions: '+ '; '.join(f"{x['interaction_date']} {x['intent']} ({x['resolution_status']})" for x in result['recent_interactions'][:3]))
        # Combine structured claim/document data with relevant policy wording, as required by the brief.
        product = c.get('product_name')
        if product:
            policy_hits = retrieve(f"Claim analysis coverage exclusions waiting period procedure for {product}", top_k=2, product_filter=product)
            if policy_hits:
                parts += ['', '**Related policy wording (context only)**']
                for hit in policy_hits:
                    parts.append(f"- {hit['product']} — {hit['section']}: {hit['text']}")
                    sources.append(f"{hit['source']} — {hit['section']}")
        parts += ['', 'This is a data-based summary, not an approval or coverage decision. A claim reviewer should confirm any final decision.']
        sources.append('claim_documents + customer_interactions SQL')
    return '\n'.join(parts), sources, 'claim_analysis' if analysis else 'claim_sql'

def _llm_answer(question, contexts):
    if not OPENAI_API_KEY: return None
    prompt='Answer only from the supplied insurance dataset/policy excerpts. If they do not establish an answer, say what is unknown. Cite source filenames and section headings. Never guarantee claim approval.\n\nCONTEXT:\n'+contexts+'\n\nQUESTION: '+question
    body=json.dumps({'model':OPENAI_MODEL,'messages':[{'role':'system','content':'You are a cautious enterprise insurance support assistant. Use only provided evidence.'},{'role':'user','content':prompt}],'temperature':0.1,'max_tokens':500,'stream':False}).encode()
    req=urllib.request.Request(OPENAI_BASE_URL.rstrip('/')+'/chat/completions',data=body,headers={'Content-Type':'application/json','Authorization':'Bearer '+OPENAI_API_KEY,'HTTP-Referer':'http://localhost:8501','X-OpenRouter-Title':'Insurance Claims & Policy Intelligence Assistant'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=45) as r: data=json.loads(r.read().decode())
        return data['choices'][0]['message']['content']
    except Exception as e:
        return None

def answer_question(question):
    q=question.strip()
    if not q: return {'answer':'Please enter a question.','route':'none','sources':[],'retrieved_chunks':[]}
    route=route_question(q); sources=[]; retrieved=[]; context=''
    if route in ('claim_sql','claim_analysis'):
        cid=extract_id(q,'CLM'); ans,sources,route_used=_claim_answer(cid,route=='claim_analysis')
        # Save API calls for tasks that benefit from synthesis: exact claim-status lookups remain SQL-only.
        if route == 'claim_analysis' and OPENAI_API_KEY and 'could not find claim' not in ans.lower():
            synthesized = _llm_answer(q, 'VERIFIED SQL CLAIM ANALYSIS AND POLICY CONTEXT:\n' + ans)
            if synthesized:
                ans = synthesized + '\n\n**Source note:** This summary is based on the structured claim/document records and retrieved policy excerpts. It is not a claim approval or coverage decision.'
        return {'answer':ans,'route':route_used,'sources':sources,'retrieved_chunks':[]}
    if route=='policy_sql':
        p=policy_lookup(q)
        ans=('**Policy record**\n'+'\n'.join(f'- {k}: {_fmt(v)}' for k,v in p.items()) if p else 'I could not find that policy ID in the policies table.')
        return {'answer':ans,'route':'policy_sql','sources':['policies + customers SQL'],'retrieved_chunks':[]}
    if route=='customer_sql':
        c=customer_lookup(q); ans=('**Customer record**\n'+'\n'.join(f'- {k}: {_fmt(v)}' for k,v in c.items()) if c else 'I could not find that customer ID in the customers table.')
        return {'answer':ans,'route':'customer_sql','sources':['customers SQL'],'retrieved_chunks':[]}
    if route=='hospital_sql':
        h=hospital_lookup(q)
        if not h: ans='Please provide a hospital ID such as HOSP1000, or the hospital name, so I can check the hospitals table.'
        elif isinstance(h,list): ans='**Hospital matches**\n'+'\n'.join('- '+'; '.join(f'{k}: {_fmt(v)}' for k,v in r.items()) for r in h)
        else: ans='**Hospital record**\n'+'\n'.join(f'- {k}: {_fmt(v)}' for k,v in h.items())
        return {'answer':ans,'route':'hospital_sql','sources':['hospitals SQL'],'retrieved_chunks':[]}
    if route=='interaction_sql':
        cid=extract_id(q,'CLM'); cust=extract_id(q,'CUST')
        if cid: rows=__import__('app.database',fromlist=['query']).query('SELECT * FROM customer_interactions WHERE UPPER(claim_id)=UPPER(?) LIMIT 10',(cid,))
        elif cust: rows=__import__('app.database',fromlist=['query']).query('SELECT * FROM customer_interactions WHERE UPPER(customer_id)=UPPER(?) LIMIT 10',(cust,))
        else: rows=[]
        ans='\n'.join('- '+'; '.join(f'{k}: {_fmt(v)}' for k,v in r.items()) for r in rows) if rows else 'Please include a claim ID (CLM...) or customer ID (CUST...) to retrieve interactions.'
        return {'answer':ans,'route':'interaction_sql','sources':['customer_interactions SQL'],'retrieved_chunks':[]}
    product=detect_product(q)
    retrieved=retrieve(q,top_k=5,product_filter=product)
    context='\n\n'.join(f"Source: {x['source']} | Product: {x['product']} | Section: {x['section']}\n{x['text']}" for x in retrieved)
    if retrieved:
        sources=[f"{x['source']} — {x['section']}" for x in retrieved]
    llm=_llm_answer(q,context) if context else None
    if llm: ans=llm
    elif retrieved:
        best=retrieved[:3]
        ans='I found the following policy wording relevant to your question:\n\n'+'\n\n'.join(f"**{x['product']} — {x['section']}**\n{x['text']}" for x in best)
        ans+='\n\n**Important:** This assistant provides information from synthetic training documents, not a binding coverage or claim decision. Confirm policy schedule, endorsements, and insurer review.'
    else:
        ans='I could not find sufficiently relevant policy text. Please name the policy product or ask a more specific question. I will not guess about coverage.'
    return {'answer':ans,'route':'policy_rag' if route=='policy_rag' else 'hybrid_or_clarify','sources':sources,'retrieved_chunks':[{'product':x['product'],'source':x['source'],'section':x['section'],'score':x['score'],'text':x['text']} for x in retrieved]}
