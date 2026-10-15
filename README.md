# Enterprise Insurance Claims & Policy Intelligence Assistant

A local, educational implementation of the project brief in `Insurance Genai project.docx`. It is more than a chatbot: it routes structured questions to SQL and policy wording questions to retrieval, and combines claim, policy, document, hospital and interaction data for claim analysis.

> **Dataset safety note:** the provided dataset and policy text are synthetic training data. Do not use this project to make real coverage, medical, fraud or claim decisions.

## 1. What is included

- `data.zip` — the exact dataset archive supplied with the project (CSV tables, 10 policy text files, and the seed evaluation set).
- `app/database.py` — imports the six CSV tables into a local SQLite database and creates lookup indexes.
- `app/tools.py` — deterministic SQL tools for claims, policies, customers, hospitals, claim documents and interactions. No arbitrary SQL from an LLM is executed.
- `app/retrieval.py` — splits the 10 policy files into section chunks, creates a TF-IDF vector index, combines vector similarity with keyword overlap (hybrid retrieval), applies product metadata filtering and a lightweight reranking score.
- `app/assistant.py` — intent router, SQL/RAG dispatch, grounded response formatting, and optional OpenAI-compatible LLM generation.
- `app/graph.py` — LangGraph orchestration when installed; deterministic fallback if LangGraph is unavailable.
- `app/api.py` — FastAPI local API.
- `streamlit_app.py` — local chat UI with source inspection and table counts.
- `app/evaluation.py` — evaluates retrieval on the provided seed gold-set.
- `tests/` — small routing tests.

## 2. Architecture mapped to the brief

```text
User -> Streamlit UI -> FastAPI /chat -> LangGraph router
                                      |-> Claims / Policy / Customer / Hospital SQL tools -> SQLite
                                      |-> Claim-document and interaction SQL tools --------> SQLite
                                      |-> Policy RAG -> section chunks -> TF-IDF vectors
                                                     -> keyword/vector hybrid fusion
                                                     -> metadata filter + reranking
                                                     -> optional LLM -> grounded answer + sources
```

The document explicitly says structured data should not be answered from a vector database. Therefore:

| Question type | Route | Why |
|---|---|---|
| “What is the status of claim CLM300001?” | SQL | Current claim status is a row in `claims.csv`. |
| “What is the maternity waiting period under Health Secure Plus?” | RAG | Waiting-period wording is in a policy text file. |
| “Analyze claim CLM300001 and check missing documents.” | SQL + policy retrieval where relevant | Joins the claim/policy/customer/hospital records and checks `claim_documents`; policy text can add context. |
| “Is hospital HOSP1001 in the network?” | SQL | Network status is a field in `hospitals.csv`. |

## 3. Dataset model

The README inside the supplied dataset reports these approximate row counts:

- `customers.csv`: 50,000 customers
- `policies.csv`: 75,000 policies
- `claims.csv`: 120,000 claims
- `claim_documents.csv`: 600,010 claim-document records
- `hospitals.csv`: 1,200 hospitals
- `customer_interactions.csv`: 180,000 interactions
- `policy_documents/`: 10 synthetic policy documents
- `evaluation_questions.csv`: seed gold-set (the file has no header row)

Main relationships:

- `customers.customer_id` joins to `policies.customer_id` and `claims.customer_id`.
- `policies.policy_id` joins to `claims.policy_id`.
- `claims.claim_id` joins to `claim_documents.claim_id` and `customer_interactions.claim_id`.
- `claims.hospital_id` joins to `hospitals.hospital_id`.

All source CSV columns are preserved as text in SQLite for robust import. Query logic can cast values to numeric types when aggregations are added.

## 4. Run it on Windows

Use Python 3.10 or 3.11. In PowerShell, open this folder:

```powershell
cd path\to\insurance_genai_project
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again. Or use `.venv\Scripts\python.exe` directly.

### Step A — import data (first run only)

```powershell
python run_setup.py
```

This reads the CSVs directly from `data.zip` and creates `data/insurance.db`. It can take a few minutes because the archive includes over one million records across the tables. The generated database is not included in the download because it is reproducible and much larger than the original archive.

### Step B — start the chat UI

```powershell
streamlit run streamlit_app.py
```

Streamlit prints a local URL, normally `http://localhost:8501`.

### Step C — (optional) start the API

Open a second terminal in the same folder, activate the environment, then run:

```powershell
uvicorn app.api:app --reload --port 8000
```

- API health and row counts: `http://127.0.0.1:8000/health`
- Interactive API docs: `http://127.0.0.1:8000/docs`
- Chat request: `POST http://127.0.0.1:8000/chat` with JSON body `{"question":"What is the status of claim CLM300001?"}`

The API imports the database automatically on first startup if it has not been initialized yet.

## 5. OpenRouter API configuration (recommended for this project)

This project uses OpenRouter for paid LLM generation. It is deliberately cost-conscious:

- Exact claim/policy/customer/hospital lookups stay SQL-only and do not call the LLM.
- Policy questions call the model only after local retrieval has found relevant policy passages.
- Claim analysis can call the model to summarize verified SQL results and retrieved policy context.
- Prompts are limited to retrieved context and the answer is capped at 500 output tokens.
- If the API is unavailable or errors, the app falls back to the grounded local answer.

### Set it up in VS Code on Windows

1. In OpenRouter, create an API key from your account dashboard. Keep it private.
2. In VS Code Explorer, copy `.env.example` and rename the copy to `.env`.
3. Paste your key after `OPENROUTER_API_KEY=`. Do not include quotes or share the key in screenshots, GitHub, or chat.
4. Keep `OPENROUTER_MODEL=deepseek/deepseek-v4-flash` as the initial low-cost model choice, or change it to a model currently available in your OpenRouter model catalog. Model prices and availability can change.
5. Restart Streamlit after changing `.env`.

Example `.env` (use your own key; never paste a real key into this README):

```dotenv
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_MODEL=deepseek/deepseek-v4-flash
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

The `python-dotenv` package loads `.env` automatically. The `.gitignore` excludes it. For cost control, monitor usage in the OpenRouter Activity dashboard and set any available key/account spending limits there. The application itself does not enforce a dollar budget.

Official references: [OpenRouter pricing](https://openrouter.ai/pricing), [model catalog](https://openrouter.ai/models), [API quickstart](https://openrouter.ai/docs/quickstart).

## 6. Try these questions

1. `What is the status of claim CLM300001?`
2. `Analyze claim CLM300001 and tell me if documents are missing.`
3. `What is the maternity waiting period under Health Secure Plus?`
4. `What is the pre-existing disease waiting period under Health Secure Plus?`
5. `Does Family Care Gold cover dental treatment?`
6. `Is hospital HOSP1001 part of the network?`
7. `Show policy POL200000`
8. `Show customer CUST100000`

IDs in the brief are examples; use IDs that actually exist in the supplied dataset if one is not found.

## 7. Evaluation and tests

```powershell
python -m app.evaluation
pytest -q
```

The evaluation output includes retrieval hit rate, topic hit rate and expected-answer term coverage. These are transparent starter metrics, not a rigorous LLM benchmark. The project brief asks learners to expand the seed evaluation set to 50–100+ items. Add representative SQL, RAG, hybrid, out-of-scope, and hallucination-resistance questions; score retrieval relevance and answer faithfulness separately.

## 8. Important limitations / next improvements

1. **Embeddings:** the baseline uses sparse TF-IDF vectors to keep setup local and avoid downloading a model. A stronger extension is sentence-transformer embeddings plus Chroma/FAISS, while keeping the same metadata and source IDs.
2. **Hybrid search:** combines TF-IDF similarity and lexical overlap. For production, add BM25 and a dedicated cross-encoder reranker.
3. **LangGraph:** the graph explicitly orchestrates routing and answer generation. The routing logic is deterministic by design; this reduces unsafe tool selection. More granular SQL/RAG nodes can be added as a learning extension.
4. **LLM:** optional and only used to synthesize from retrieved context. If unavailable or failing, a local extractive answer is returned.
5. **Guardrails:** no arbitrary SQL generation, product filtering, low-evidence fallback, source names, and a no-guarantee disclaimer. This is a demo, not a security-hardened enterprise system.
6. **MCP:** the project brief lists MCP as an advanced option, not a mandatory component. A follow-up extension could expose read-only claim lookup and policy retrieval as MCP tools.
7. **Privacy:** the sample contains synthetic data, but any real deployment would need authentication, authorization, PII masking, audit logging, rate limiting, secrets management and retention controls.

## 9. How to explain this in a project viva

- **Why SQL and RAG separately?** A claim status is exact structured data; policy clauses are unstructured text. Vector similarity is not a reliable source for exact claim fields.
- **What is chunking?** Policy files are split at numbered section boundaries so a retrieved passage can be cited to a product and section.
- **What is hybrid retrieval?** TF-IDF vector similarity is combined with exact keyword overlap, improving retrieval when a user uses policy terms.
- **What is metadata filtering?** If the question names Health Secure Plus, candidate chunks are limited to that product rather than mixing clauses from other policies.
- **What is reranking?** The initial combined score is adjusted to prioritize matching section headings, then the top passages are shown or sent to the LLM.
- **How is hallucination limited?** The answerer is instructed to use supplied excerpts only; local mode quotes source sections; missing evidence triggers a clarification rather than a coverage guess.
- **Why FastAPI and Streamlit?** FastAPI exposes a reusable API; Streamlit gives a quick local demo UI.
