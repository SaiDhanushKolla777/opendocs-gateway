# OpenDocs Gateway

OpenDocs Gateway is a document intelligence application that runs on a single AMD MI300X GPU. You upload documents (PDFs, text files), and the system lets you ask questions about them, extract structured data, compare documents against each other, and run queries across multiple documents at once — all with proper citations back to the source text.

The backend talks to a vLLM server running an open-weight model (we used Qwen2.5-7B-Instruct, but any OpenAI-compatible endpoint works). The frontend is a Next.js app with a clean chat-style interface. Everything is designed for one GPU, one endpoint, no distributed inference.

---

## What makes this different

Most RAG applications follow a standard pattern: chunk, embed, vector store, retrieve, generate. OpenDocs Gateway makes several design choices that diverge from the norm:

**Hybrid retrieval with optional FAISS ANN indexing.** Dense embeddings (sentence-transformers) are fused with TF-IDF scoring using Reciprocal Rank Fusion — the same technique used by Elasticsearch and state-of-the-art IR systems. Embeddings are stored as raw BLOBs in the same SQLite table as the chunks. No ChromaDB, no Pinecone, no separate vector store. For document-scale workloads, brute-force scoring is used automatically. For corpus-scale workloads (thousands to millions of chunks), FAISS HNSW indexes are built per-document at ingest time and used for sub-linear approximate nearest neighbor search. The system selects the right strategy automatically and falls back gracefully.

**Citations reflect what the LLM actually used, not just what matched the query.** After the LLM generates an answer, all context chunks are re-ranked by their overlap with the answer text. A chunk that scored high on retrieval but wasn't drawn from in the response gets demoted. This two-stage pipeline (retrieve → generate → re-cite) is uncommon — most systems attach citations based solely on the retrieval step.

**Intent classification without an LLM call.** Every incoming message is classified as a new question, a follow-up, or conversational filler using pure word-set analysis — no extra model inference. When a user says "thanks", the system skips chunk scoring, embedding lookups, and context assembly entirely, responding with just a lightweight LLM call (100 tokens, no retrieval). This saves meaningful GPU time in real conversations.

**Retrieval queries are enriched from conversation history.** When a follow-up is detected, the search query is augmented with terms from prior substantive user messages. So "tell me more" doesn't search for the word "more" — it searches for what was discussed in previous turns.

**Extraction schemas are generated per-document.** Instead of hardcoded templates, a first LLM pass reads sampled chunks to detect the document type and generate an appropriate extraction schema. A novel gets characters, themes, plot structure. A contract gets parties, dates, obligations. A research paper gets methodology, findings, conclusions. No configuration needed.

**Comparison adapts to document relationships.** Text fingerprinting and title matching detect whether two documents are identical, versions of each other, or completely different — then a different prompt runs for each case. Identical documents are caught instantly without an LLM call.

**Zero-infrastructure deployment.** One SQLite file, one filesystem directory, one GPU. No Redis, no PostgreSQL, no message queue, no external vector store service. FAISS indexes are persisted as flat files alongside the database. The entire backend is a single Python process.

---

## What it does

### Grounded Q&A

Pick a document, ask a question, get an answer that only uses information from that document. The system retrieves relevant chunks, sends them to the LLM with the question, and returns the answer with citations pointing to the exact passages it drew from.

The conversation is stateful — you can ask follow-up questions like "tell me more about that" or "what about the second chapter?" and the system understands you're building on the prior exchange. It knows the difference between a real question, a follow-up, and a casual remark like "thanks" (which it handles without wasting a GPU call on retrieval).

### Multi-document analysis

Select two or more documents and ask questions across all of them. The retrieval is balanced — it pulls relevant chunks from each document proportionally rather than letting one document dominate the results. This means if you ask "what are these two docs about?", you actually get information from both.

### Structured extraction

Upload a document and the system figures out what kind of document it is (novel, contract, research paper, manual, etc.) and generates an appropriate extraction schema. A novel gets characters, themes, plot structure. A contract gets parties, dates, obligations, clauses. You get clean JSON output.

This is done through a two-step LLM process: first it reads a sample of the document to detect its type and build the schema, then it runs the actual extraction across a broad spread of chunks.

### Document comparison

Pick two documents and the system tells you what's different. It's smart about what kind of comparison to run:

- **Same document, different versions** (detected by matching titles or high text overlap) — you get specific additions, removals, and modifications with section-level detail.
- **Completely different documents** (like a novel vs. a textbook) — you get what each document covers, key differences in content and purpose, and any shared themes.
- **Identical documents** — caught early without burning a GPU call. Just tells you they're the same.

### Metrics dashboard

Tracks request count, latency percentiles (P50/P95/P99), average input and output token usage, total tokens processed, error rates, and schema validation rates. All in-memory, updated in real time.

---

## How the retrieval works

The retrieval pipeline combines dense semantic embeddings with keyword-based scoring via hybrid fusion:

### Dual scoring

Each chunk is scored by two independent signals:

1. **Dense semantic similarity** — Chunks are embedded at upload time using sentence-transformers (`all-MiniLM-L6-v2` by default). At query time, the query is embedded and scored against every chunk via cosine similarity. This captures meaning: "What is the protagonist's flaw?" matches chunks about character weaknesses even if the word "flaw" never appears.

2. **TF-IDF-style lexical scoring** — Term frequency weighted by inverse document frequency, with proper noun boosting (2.5x weight for capitalized words like names and places), bigram phrase matching, and stopword filtering. This captures precision: when you ask about "Elizabeth Bennet", chunks containing her name rank high regardless of semantic distance.

### FAISS ANN indexing

When FAISS is enabled (default), a per-document ANN index is built automatically at ingest time alongside the embeddings. The system supports two index types:

- **HNSW (Hierarchical Navigable Small World)** — Used by default for documents with 16+ chunks. Provides sub-linear search time with configurable build quality (`FAISS_HNSW_M`, `FAISS_HNSW_EF_CONSTRUCTION`) and query quality (`FAISS_HNSW_EF_SEARCH`). This is the same algorithm used by major vector databases internally.
- **Flat (exact inner product)** — Used automatically for small documents where the overhead of building a graph isn't worth it. Gives exact results with zero approximation error.

Indexes are persisted to disk as `.faiss` files and lazily loaded into an in-memory cache on first query. For multi-document queries, results from per-document indexes are merged and re-ranked.

When FAISS is available, `score_chunks` uses the ANN index for the semantic scoring pass instead of brute-force dot products. This makes no difference for small documents but becomes critical at corpus scale — searching 100,000 chunks with HNSW takes milliseconds instead of seconds.

### Fusion

The two score lists are merged using **Reciprocal Rank Fusion** (RRF): each chunk gets `1/(k + rank_tfidf) + 1/(k + rank_semantic)` where `k=60`. RRF is robust — it doesn't need careful weight tuning and handles the different score distributions of lexical and semantic systems naturally. A weighted linear blend mode is also available via configuration.

### Post-retrieval pipeline

3. **Neighbor chunk expansion** — After selecting the top chunks, the system pulls in adjacent chunks (the one before and after each selected chunk). This gives the LLM continuous passages rather than isolated fragments.

4. **Answer-based citation re-ranking** — After the LLM generates its answer, all context chunks are re-ranked by how much they overlap with the actual answer text (token overlap + bigram phrase bonus). The citations you see are the ones that genuinely supported what the LLM said, not just the ones that matched the query.

### Graceful degradation

The retrieval pipeline degrades gracefully through multiple fallback layers:

1. If FAISS is available → uses ANN index for fast semantic scoring
2. If FAISS is unavailable or no index exists → falls back to brute-force dot products
3. If `sentence-transformers` is not installed or embeddings are missing → falls back to TF-IDF-only scoring

Embeddings for older documents (uploaded before RAG was enabled) are backfilled on the first query, and their FAISS indexes are rebuilt at that time.

The retrieval settings (number of chunks, context budget, token limits, fusion mode, weights, FAISS parameters) are all configurable through environment variables.

---

## How conversation works

The system classifies every incoming message into one of three intents — without making an LLM call:

- **New question** — Contains substantive words or question words. Gets full retrieval and LLM processing.
- **Follow-up** — Short message with referential words ("more detail", "why", "how about") and there's conversation history. The search query is enriched with terms from recent questions so retrieval stays relevant to the thread. The LLM prompt tells it to expand with new information, not repeat itself.
- **Conversational** — Things like "thanks", "ok", "got it" where every word is filler. The system sends these to the LLM with just the conversation history (no retrieval, no context) and gets a brief natural response. No GPU time wasted on chunk scoring.

This classification uses content analysis (checking for action words, question words, content density) rather than pattern matching against a hardcoded list, so it handles edge cases naturally.

---

## Project structure

```
opendocs-gateway/
├── api/                          # FastAPI backend
│   ├── app/
│   │   ├── config.py             # All settings from env vars
│   │   ├── main.py               # FastAPI app, CORS, router setup
│   │   ├── dependencies.py       # DB session dependency
│   │   ├── db/                   # SQLAlchemy models, session, repositories
│   │   ├── models/               # Pydantic models (request/response, chunk, citation)
│   │   ├── routers/              # API endpoints
│   │   │   ├── ask.py            # Single + multi-doc Q&A with intent classification
│   │   │   ├── compare.py        # Document comparison
│   │   │   ├── documents.py      # Upload, list, get, delete
│   │   │   ├── extract.py        # Structured extraction
│   │   │   ├── health.py         # Health check
│   │   │   ├── metrics.py        # Observability metrics
│   │   │   └── reports.py        # Report generation
│   │   ├── services/             # Business logic
│   │   │   ├── comparison_service.py   # Mode-aware doc comparison
│   │   │   ├── embedding_service.py    # Dense embeddings (sentence-transformers)
│   │   │   ├── extraction_service.py   # Adaptive schema detection + extraction
│   │   │   ├── faiss_index.py          # FAISS ANN index management (HNSW/flat)
│   │   │   ├── ingestion_service.py    # Text extraction, chunking, embedding
│   │   │   ├── llm_service.py          # vLLM client (OpenAI SDK)
│   │   │   ├── metrics_service.py      # In-memory metrics tracking
│   │   │   └── retrieval_service.py    # Hybrid scoring, FAISS ANN, fusion, re-ranking
│   │   └── utils/                # Prompts, token budgeting, validation
│   └── requirements.txt
├── frontend/                     # Next.js 14 (App Router)
│   └── src/
│       ├── app/                  # Pages: ask, multi, extract, compare, documents, etc.
│       ├── components/           # Sidebar, DocumentSelector, CitationCard
│       └── lib/api.ts            # API client functions
├── scripts/                      # Run scripts, e2e test
├── docker-compose.yml            # Backend + frontend (vLLM is external)
├── .env.example                  # All configuration options
└── data/                         # Sample documents
```

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn, SQLAlchemy, Pydantic |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2), NumPy |
| ANN Index | FAISS (HNSW or flat inner-product, per-document indexes) |
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS |
| LLM serving | vLLM (any OpenAI-compatible endpoint) |
| Model | Qwen/Qwen2.5-7B-Instruct (or any model your vLLM serves) |
| Database | SQLite (documents + chunks + embeddings) |
| File storage | Local filesystem (uploads + FAISS indexes) |
| GPU | AMD Instinct MI300X (192GB HBM3) |

---

## Getting started

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- A running vLLM server with an OpenAI-compatible API (or any compatible endpoint)

### 1. Clone and configure

```bash
git clone https://github.com/SaiDhanushKolla777/opendocs-gateway.git
cd opendocs-gateway
cp .env.example .env
```

Edit `.env` and set at minimum:
- `VLLM_BASE_URL` — your vLLM server URL (e.g., `http://localhost:8001/v1`)
- `VLLM_MODEL` — the model name vLLM is serving (e.g., `Qwen/Qwen2.5-7B-Instruct`)

### 2. Start the backend

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p data data/uploads
export PYTHONPATH=$PWD
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be at `http://localhost:8000` and Swagger docs at `http://localhost:8000/docs`.

### 3. Start the frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Open `http://localhost:3000` in your browser.

### Alternative: Docker

```bash
docker compose up --build
```

This starts the backend and frontend. vLLM runs separately — set `VLLM_BASE_URL` in your `.env` to point at it.

---

## Running on AMD MI300X (ROCm)

If you're on an MI300X GPU droplet with a ROCm container and vLLM already running:

```bash
# Inside the ROCm container
cd /path/to/opendocs-gateway/api
pip install -r requirements.txt
mkdir -p data data/uploads
PYTHONPATH=$PWD uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (needs Node.js)
cd /path/to/opendocs-gateway/frontend
npm install
NEXT_PUBLIC_API_URL=http://<your-gpu-ip>:8000 npm run dev -- -H 0.0.0.0
```

Set `VLLM_BASE_URL` to wherever vLLM is listening (usually `http://localhost:8001/v1` if it's on the same machine).

---

## API reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/documents/upload` | POST | Upload a PDF or TXT file (multipart form) |
| `/documents` | GET | List all uploaded documents |
| `/documents/{id}` | GET | Get document metadata |
| `/documents/{id}` | DELETE | Delete a document |
| `/documents/{id}/ask` | POST | Ask a question about a single document |
| `/documents/ask-multi` | POST | Ask across multiple documents |
| `/documents/{id}/extract` | POST | Extract structured data as JSON |
| `/compare` | POST | Compare two documents |
| `/metrics` | GET | Get inference metrics |
| `/reports` | POST | Generate a report |

### Ask endpoint body

```json
{
  "question": "What is the main theme?",
  "answer_mode": "plain_english",
  "history": [
    {"role": "user", "content": "previous question"},
    {"role": "assistant", "content": "previous answer"}
  ]
}
```

`answer_mode` options: `plain_english`, `concise_bullets`, `executive_summary`, `student_friendly`, `policy_legal`.

The `history` field is optional — include it for multi-turn conversations.

---

## Configuration

All settings are controlled through environment variables (see `.env.example`):

| Variable | Default | What it does |
|----------|---------|-------------|
| `VLLM_BASE_URL` | `http://localhost:8001/v1` | vLLM server endpoint |
| `VLLM_MODEL` | (empty) | Model name to use |
| `MAX_RETRIEVED_CHUNKS` | `6` | Max chunks retrieved per query |
| `MAX_CONTEXT_CHARS` | `32000` | Character budget for LLM context |
| `MAX_ANSWER_TOKENS` | `1024` | Max tokens in LLM response |
| `MAX_EXTRACTION_TOKENS` | `2048` | Max tokens for extraction |
| `MAX_COMPARE_CONTEXT_CHARS` | `24000` | Character budget for comparison |
| `MAX_MULTI_DOCS` | `5` | Max documents in multi-doc query |
| `MAX_UPLOAD_MB` | `50` | Max upload file size |
| `RAG_ENABLED` | `true` | Enable hybrid dense+TF-IDF retrieval |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `RAG_FUSION_MODE` | `rrf` | Fusion strategy: `rrf` or `weighted` |
| `RAG_SEMANTIC_WEIGHT` | `0.55` | Semantic weight (weighted mode only) |
| `RAG_TFIDF_WEIGHT` | `0.45` | TF-IDF weight (weighted mode only) |
| `RRF_K` | `60` | RRF constant (higher = more uniform blending) |
| `FAISS_ENABLED` | `true` | Enable FAISS ANN indexing for semantic search |
| `FAISS_INDEX_DIR` | `./data/faiss_indexes` | Directory for persisted FAISS index files |
| `FAISS_USE_HNSW` | `true` | Use HNSW (approximate) vs flat (exact) indexes |
| `FAISS_HNSW_M` | `32` | HNSW graph connectivity (higher = better recall, more memory) |
| `FAISS_HNSW_EF_CONSTRUCTION` | `64` | HNSW build-time quality (higher = slower build, better index) |
| `FAISS_HNSW_EF_SEARCH` | `32` | HNSW query-time quality (higher = slower search, better recall) |
| `FAISS_NPROBE` | `8` | IVF probe count (for future IVF index support) |

---


## Screenshot

<img width="2499" height="1296" alt="image" src="https://github.com/user-attachments/assets/742f9e0c-43cb-48ab-98c0-093cae9856eb" />


<img width="2447" height="1286" alt="image" src="https://github.com/user-attachments/assets/fa101244-ed08-402b-ae6a-e8be47a1793d" />


<img width="2535" height="1242" alt="image" src="https://github.com/user-attachments/assets/af89a8f7-086b-446a-850d-bae40735b03f" />


## Current limitations

- **Single vLLM endpoint.** The system talks to one model endpoint. No multi-model routing or fallbacks.
- **SQLite only.** Fine for single-user or small team usage. Would need PostgreSQL for production multi-user deployments.
- **Metrics are in-memory.** They reset when the backend restarts. No persistent metrics storage.
- **No authentication.** Anyone with access to the URL can use the system. Add a reverse proxy or API key middleware for production.

---

## What could be added next

- Reranker model (cross-encoder) as a third scoring pass after fusion
- Streaming responses (SSE) for real-time token output in the chat UI
- PDF report export from the reports feature
- Redis for caching LLM responses to repeated queries
- Authentication and API key management
- PostgreSQL for multi-user deployments



