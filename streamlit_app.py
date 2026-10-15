import streamlit as st
from app.graph import run_assistant
from app.database import initialize_database, table_counts
from app.settings import OPENROUTER_API_KEY, OPENROUTER_MODEL
st.set_page_config(page_title='Insurance Intelligence Assistant',page_icon='🛡️',layout='wide')
st.title('🛡️ Insurance Claims & Policy Intelligence Assistant')
st.caption('Local project demo • SQL for structured records • Hybrid RAG for policy documents')
with st.sidebar:
 st.subheader('Project status')
 if OPENROUTER_API_KEY:
  st.success(f'OpenRouter enabled · {OPENROUTER_MODEL}')
 else:
  st.warning('OpenRouter not configured — local grounded mode')
 if st.button('Initialize / verify dataset'):
  with st.spinner('Importing the CSV dataset into SQLite; first run can take a few minutes...'):
   st.success(initialize_database())
 try:
  counts=table_counts()
  for table,count in counts.items(): st.metric(table.replace('_',' ').title(),f'{count:,}')
 except Exception as e: st.warning(f'Database is not ready: {e}')
 st.divider(); st.markdown('**Try these questions**')
 examples=['What is the status of claim CLM300001?','Analyze claim CLM300001 and tell me if documents are missing.','What is the maternity waiting period under Health Secure Plus?','Does Family Care Gold cover dental treatment?','Is hospital HOSP1001 part of the network?']
 for ex in examples:
  if st.button(ex,key=ex): st.session_state.question=ex
q=st.text_area('Ask an insurance question',value=st.session_state.get('question',''),height=100,placeholder='e.g. What is the pre-existing disease waiting period under Health Secure Plus?')
if st.button('Ask assistant',type='primary') and q.strip():
 with st.spinner('Routing to SQL tools and/or policy retrieval...'):
  try: result=run_assistant(q)
  except Exception as e: st.error(f'Could not answer: {e}'); st.stop()
 st.markdown(result['answer'])
 c1,c2=st.columns([1,2])
 with c1: st.info(f"**Route used:** `{result['route']}`")
 with c2: st.write('**Sources:** '+('; '.join(result['sources']) if result['sources'] else 'No source found'))
 if result['retrieved_chunks']:
  with st.expander('Inspect retrieved policy chunks and reranking scores'):
   for item in result['retrieved_chunks']:
    st.markdown(f"**{item['product']} | {item['section']}** — score `{item['score']}`")
    st.caption(item['source']); st.write(item['text'])
st.divider()
st.caption('Synthetic educational dataset. Do not use this demo to make real insurance or medical decisions. Sensitive claim data should be handled only in authorized environments.')
