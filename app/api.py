from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .graph import run_assistant
from .database import initialize_database, table_counts
app=FastAPI(title='Insurance Claims & Policy Intelligence Assistant',version='1.0.0',description='Local RAG + SQL insurance assistant')
class ChatRequest(BaseModel): question: str = Field(min_length=1,max_length=2000)
@app.on_event('startup')
def startup(): initialize_database()
@app.get('/health')
def health(): return {'status':'ok','database':table_counts()}
@app.post('/chat')
def chat(body: ChatRequest):
    try: return run_assistant(body.question)
    except Exception as e: raise HTTPException(status_code=500,detail=f'Assistant error: {type(e).__name__}: {e}')
@app.get('/claims/{claim_id}')
def claim(claim_id: str):
    if not claim_id.upper().startswith('CLM'): raise HTTPException(status_code=400,detail='Claim ID should start with CLM')
    result=run_assistant(f'Analyze claim {claim_id} and check missing documents')
    if 'could not find claim' in result['answer'].lower(): raise HTTPException(status_code=404,detail=result['answer'])
    return result
