# OpenDocs Gateway

**A long-context, citation-grounded document intelligence system built with vLLM for a single AMD MI300X GPU.**

OpenDocs Gateway helps users upload or ingest public documents and get grounded answers with citations, plain-English summaries, structured JSON extraction, document version comparison, and shareable reports. It is designed as a **single-node inference application** that makes real use of the MI300X: large GPU memory, long-context inference, larger retrieval context packs, and multi-document comparison on one GPU.

## Features

- **Document upload & ingestion** — PDF upload, text extraction, chunking, metadata storage
- **Grounded Q&A** — Single- and multi-document question answering with citations and insufficient-evidence signals
- **Structured extraction** — Schema-based JSON extraction (deadlines, requirements, contacts, etc.)
- **Document comparison** — “What changed?” between old and new document versions
- **Multi-document analysis** — Questions across multiple uploaded documents
- **Shareable reports** — Report page with summary, facts, citations, export
- **Benchmark / observability** — Metrics and latency visibility for single-GPU deployment

## Architecture

- **Backend**: FastAPI (orchestration, retrieval, validation, metrics)
- **Frontend**: Next.js (React)
- **Model serving**: One vLLM OpenAI-compatible endpoint (configured via `VLLM_BASE_URL`, `VLLM_MODEL`, `VLLM_API_KEY`)
- **Storage**: SQLite + local file storage for v1
- **Retrieval**: Lightweight in-process retrieval (chunking, scoring, context assembly); designed to allow vector/rerank later

Single-GPU design: no distributed inference; one vLLM endpoint; configurable max context, chunks, and concurrency.

## Local setup

### Prerequisites

- Python 3.11+
- Node 18+ (for frontend)
- A running vLLM server (OpenAI-compatible) or mock

### Backend

```bash
cd opendocs-gateway
cp .env.example .env
# Edit .env: set VLLM_BASE_URL (and optionally VLLM_MODEL, VLLM_API_KEY)

cd api
python3 -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
mkdir -p data data/uploads
export PYTHONPATH=$PWD
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or from repo root: `./scripts/run-backend.sh`

API: http://localhost:8000  
Docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:3000

## Docker

```bash
cp .env.example .env
# Set VLLM_BASE_URL to your vLLM server (e.g. http://host.docker.internal:8001/v1)

docker compose up --build
```

- API: http://localhost:8000  
- Frontend: http://localhost:3000  

vLLM is not included in the stack; run it separately and point `VLLM_BASE_URL` to it.

## API examples

- `GET /health` — Health check
- `POST /documents/upload` — Upload PDF (multipart form, file field)
- `GET /documents` — List documents
- `GET /documents/{id}` — Get document metadata
- `POST /documents/{id}/ask` — Ask a question (body: `question`, `answer_mode`, optional `max_citations`)
- `POST /documents/ask-multi` — Multi-document ask (body: `document_ids`, `question`, `answer_mode`)
- `POST /documents/{id}/extract` — Structured extraction (body: `extraction_type`, optional `schema_request`)
- `POST /compare` — Compare documents (body: `old_document_id`, `new_document_id`)
- `GET /metrics` — Metrics (p50/p95 latency, request count, schema valid rate)
- `GET /reports/{report_id}` — Get report

## Benchmark

- `GET /metrics` and `GET /benchmarks/summary` expose request count, active requests, p50/p95 latency, and schema-valid rate for the single-GPU deployment.

## Roadmap

- Vector search / reranking for retrieval
- Optional Redis for caching
- PDF report export
- Auth / API keys

## Known limitations

- v1 retrieval is keyword-style; no vector or reranker yet.
- Single vLLM endpoint only; no multi-model orchestration.
- Reports stored in-memory (no persistence across restarts).

## Why this project

OpenDocs Gateway is a **single-GPU document intelligence system** and an **MI300X-aware long-context serving project**. It is built to showcase long-context document understanding, single-node high-memory inference, and practical throughput on one MI300X GPU, while remaining useful for real document workflows (policy, handbooks, guidelines, release notes).
