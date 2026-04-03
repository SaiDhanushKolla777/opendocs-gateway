"""Dense embeddings for hybrid RAG (sentence-transformers + TF-IDF fusion)."""
from __future__ import annotations

import logging
import threading
from typing import List, Optional, Tuple, TYPE_CHECKING

import numpy as np

from app.config import get_settings
from app.db.repositories import get_chunks_by_document, update_chunk_embeddings_batch

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Chunk

logger = logging.getLogger(__name__)

_model = None
_model_name_loaded: Optional[str] = None
_model_lock = threading.Lock()


def embedding_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


def _get_model():
    global _model, _model_name_loaded
    s = get_settings()
    name = s.embedding_model
    with _model_lock:
        if _model is None or _model_name_loaded != name:
            if not embedding_available():
                raise RuntimeError(
                    "sentence-transformers is not installed. "
                    "Install API deps: pip install sentence-transformers numpy"
                )
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model: %s", name)
            _model = SentenceTransformer(name)
            _model_name_loaded = name
        return _model


def embedding_to_bytes(vec: np.ndarray) -> bytes:
    return np.asarray(vec, dtype=np.float32).tobytes()


def bytes_to_embedding(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32).copy()


def encode_texts(texts: List[str]) -> np.ndarray:
    """Return L2-normalized embeddings, shape (n, dim)."""
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    model = _get_model()
    arr = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(arr, dtype=np.float32)


def encode_query(query: str) -> np.ndarray:
    """Single query embedding (L2-normalized)."""
    return encode_texts([query.strip() or " "])[0]


def embed_document_chunks(db: "Session", document_id: str) -> int:
    """Compute and store embeddings for all chunks of a document (after ingest)."""
    s = get_settings()
    if not s.rag_enabled or not embedding_available():
        return 0
    rows = get_chunks_by_document(db, document_id)
    if not rows:
        return 0
    texts = [r.text for r in rows]
    try:
        embs = encode_texts(texts)
    except Exception as e:
        logger.exception("Embedding failed for document %s: %s", document_id, e)
        return 0
    updates: List[Tuple[str, bytes]] = []
    for row, vec in zip(rows, embs):
        updates.append((row.id, embedding_to_bytes(vec)))
    update_chunk_embeddings_batch(db, updates)
    return len(updates)


def semantic_similarity_scores(query: str, chunks: List["Chunk"]) -> List[float]:
    """Cosine similarity scores (query vs each chunk embedding), same order as chunks."""
    if not chunks:
        return []
    q = encode_query(query)
    scores: List[float] = []
    for c in chunks:
        if not c.embedding:
            scores.append(-1.0)
            continue
        v = bytes_to_embedding(c.embedding)
        scores.append(float(np.dot(q, v)))
    return scores


def ensure_chunk_embeddings(db: "Session", chunks: List["Chunk"]) -> None:
    """Backfill missing embeddings in DB and attach bytes to Chunk objects."""
    s = get_settings()
    if not s.rag_enabled or not embedding_available():
        return
    missing = [c for c in chunks if not c.embedding]
    if not missing:
        return
    texts = [c.text for c in missing]
    try:
        embs = encode_texts(texts)
    except Exception as e:
        logger.warning("Embedding backfill failed (TF-IDF only): %s", e)
        return
    updates: List[Tuple[str, bytes]] = []
    for ch, vec in zip(missing, embs):
        blob = embedding_to_bytes(vec)
        updates.append((ch.chunk_id, blob))
        ch.embedding = blob
    update_chunk_embeddings_batch(db, updates)
