"""Deterministic SQL tools for structured insurance data. No arbitrary LLM-generated SQL is executed."""
import re
from .database import query

def extract_id(text, prefix):
    m=re.search(r'\b'+prefix+r'\d+\b', text, re.I)
    return m.group(0).upper() if m else None

def claim_details(claim_id):
    sql='''SELECT c.*, p.product_name, p.policy_status, p.policy_start_date, p.policy_end_date,
      p.sum_insured, p.co_pay_pct, p.deductible, cu.customer_name, h.hospital_name, h.city AS hospital_city,
      h.network_status
      FROM claims c LEFT JOIN policies p ON c.policy_id=p.policy_id
      LEFT JOIN customers cu ON c.customer_id=cu.customer_id
      LEFT JOIN hospitals h ON c.hospital_id=h.hospital_id WHERE UPPER(c.claim_id)=UPPER(?) LIMIT 1'''
    rows=query(sql,(claim_id,)); return rows[0] if rows else None

def claim_documents(claim_id):
    return query('''SELECT document_type, upload_status, verification_status, file_type
      FROM claim_documents WHERE UPPER(claim_id)=UPPER(?) ORDER BY document_type''',(claim_id,))

def claim_summary(claim_id):
    c=claim_details(claim_id)
    if not c: return None
    docs=claim_documents(claim_id)
    missing=[d for d in docs if (d.get('upload_status') or '').lower()=='missing']
    pending=[d for d in docs if (d.get('upload_status') or '').lower()=='uploaded' and (d.get('verification_status') or '').lower() not in ('verified','approved')]
    rejected=[d for d in docs if (d.get('verification_status') or '').lower()=='rejected']
    interactions=query('''SELECT interaction_date, channel, intent, sentiment, resolution_status FROM customer_interactions
       WHERE UPPER(claim_id)=UPPER(?) ORDER BY interaction_date DESC LIMIT 5''',(claim_id,))
    return {'claim':c,'documents':docs,'missing_documents':missing,'pending_documents':pending,'rejected_documents':rejected,'recent_interactions':interactions}

def hospital_lookup(question):
    hid=extract_id(question,'HOSP')
    if hid:
        r=query('SELECT * FROM hospitals WHERE UPPER(hospital_id)=UPPER(?) LIMIT 1',(hid,)); return r[0] if r else None
    m=re.search(r'(?:hospital|provider)\s+([A-Za-z][A-Za-z0-9 &.-]{2,60})',question,re.I)
    if m:
        name=m.group(1).strip(' ?.!,')
        r=query('SELECT * FROM hospitals WHERE LOWER(hospital_name) LIKE ? LIMIT 5',('%'+name.lower()+'%',)); return r
    return None

def customer_lookup(question):
    cid=extract_id(question,'CUST')
    if cid:
        r=query('SELECT * FROM customers WHERE UPPER(customer_id)=UPPER(?) LIMIT 1',(cid,)); return r[0] if r else None
    return None

def policy_lookup(question):
    pid=extract_id(question,'POL')
    if pid:
        r=query('''SELECT p.*, c.customer_name FROM policies p LEFT JOIN customers c ON p.customer_id=c.customer_id WHERE UPPER(p.policy_id)=UPPER(?) LIMIT 1''',(pid,)); return r[0] if r else None
    return None
