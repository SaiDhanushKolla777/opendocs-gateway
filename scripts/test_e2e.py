"""End-to-end test: upload Pride and Prejudice, ask a question, extract, check metrics."""
import time
import json
from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)

# 1. Upload
print("=== UPLOAD ===")
t0 = time.time()
with open("/opendocs-api/data/pride-and-prejudice.txt", "rb") as f:
    r = c.post("/documents/upload", files={"file": ("pride-and-prejudice.txt", f, "text/plain")})
print(f"Status: {r.status_code} ({time.time()-t0:.2f}s)")
data = r.json()
doc_id = data["document_id"]
print(f"Doc ID: {doc_id}")
print(f"Title:  {data['title']}")

# 2. Check chunks
from app.dependencies import get_db_gen
from app.services.ingestion_service import document_to_chunks
db = next(get_db_gen())
chunks = document_to_chunks(db, doc_id)
print(f"Chunks: {len(chunks)}")
print(f"Total chars: {sum(c.char_length for c in chunks):,}")
print()

# 3. Ask a question
print("=== Q&A ===")
t0 = time.time()
r = c.post(f"/documents/{doc_id}/ask", json={
    "question": "What is Mr. Darcy's opinion of Elizabeth Bennet when they first meet?",
    "answer_mode": "plain_english",
})
elapsed = time.time() - t0
ans = r.json()
print(f"Status: {r.status_code} ({elapsed:.2f}s)")
print(f"Answer: {ans['answer'][:600]}")
print(f"Citations: {len(ans['citations'])}")
for ci in ans["citations"][:3]:
    page = ci.get("page_number", "?")
    print(f"  - [p.{page}] {ci['snippet'][:100]}...")
print(f"Insufficient evidence: {ans['insufficient_evidence']}")
print()

# 4. Metrics
r = c.get("/metrics")
print("=== METRICS ===")
print(json.dumps(r.json(), indent=2))
