"""FAISS ANN index management for corpus-scale semantic search.

Maintains per-document FAISS indexes on disk, supporting both flat (exact)
and HNSW (approximate) index types. Indexes are lazily loaded and cached
in memory with a global lock for thread safety.
"""
from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)

_faiss = None
_faiss_import_attempted = False

_index_cache: Dict[str, "faiss.Index"] = {}  # type: ignore[name-defined]
_id_map_cache: Dict[str, List[str]] = {}
_lock = threading.Lock()


def _import_faiss():
    """Lazy-import faiss so the app still starts when faiss-cpu is missing."""
    global _faiss, _faiss_import_attempted
    if _faiss_import_attempted:
        return _faiss
    _faiss_import_attempted = True
    try:
        import faiss as _f
        _faiss = _f
        logger.info("FAISS loaded (version %s)", getattr(_f, "__version__", "unknown"))
    except ImportError:
        logger.warning(
            "faiss-cpu is not installed — FAISS ANN index disabled. "
            "Install with: pip install faiss-cpu"
        )
        _faiss = None
    return _faiss


def faiss_available() -> bool:
    return _import_faiss() is not None


def _index_dir() -> Path:
    s = get_settings()
    p = Path(s.faiss_index_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _index_path(document_id: str) -> Path:
    return _index_dir() / f"{document_id}.faiss"


def _id_map_path(document_id: str) -> Path:
    return _index_dir() / f"{document_id}.ids"


def _build_index(dim: int, n_vectors: int) -> "faiss.Index":  # type: ignore[name-defined]
    """Build a FAISS index appropriate for the corpus size and config."""
    faiss = _import_faiss()
    s = get_settings()

    if s.faiss_use_hnsw and n_vectors >= 16:
        index = faiss.IndexHNSWFlat(dim, s.faiss_hnsw_m)
        index.hnsw.efConstruction = s.faiss_hnsw_ef_construction
        index.hnsw.efSearch = s.faiss_hnsw_ef_search
        logger.debug(
            "Building HNSW index: dim=%d, M=%d, efConstruction=%d",
            dim, s.faiss_hnsw_m, s.faiss_hnsw_ef_construction,
        )
    else:
        index = faiss.IndexFlatIP(dim)
        logger.debug("Building flat inner-product index: dim=%d", dim)

    return index


def _save_id_map(document_id: str, chunk_ids: List[str]) -> None:
    path = _id_map_path(document_id)
    path.write_text("\n".join(chunk_ids), encoding="utf-8")


def _load_id_map(document_id: str) -> Optional[List[str]]:
    path = _id_map_path(document_id)
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    return text.split("\n")


def build_document_index(
    document_id: str,
    chunk_ids: List[str],
    embeddings: np.ndarray,
) -> bool:
    """Build and persist a FAISS index for a single document's chunks.

    Args:
        document_id: Unique document identifier.
        chunk_ids: Ordered list of chunk IDs matching the embedding rows.
        embeddings: (N, dim) float32 array of L2-normalized vectors.

    Returns:
        True if the index was built successfully.
    """
    faiss = _import_faiss()
    if faiss is None:
        return False

    s = get_settings()
    if not s.faiss_enabled:
        return False

    if embeddings.ndim != 2 or embeddings.shape[0] == 0:
        logger.warning("Skipping FAISS index for %s: empty or invalid embeddings", document_id)
        return False

    if len(chunk_ids) != embeddings.shape[0]:
        logger.error(
            "chunk_ids length (%d) != embeddings rows (%d) for document %s",
            len(chunk_ids), embeddings.shape[0], document_id,
        )
        return False

    n, dim = embeddings.shape
    vecs = np.ascontiguousarray(embeddings, dtype=np.float32)

    with _lock:
        try:
            index = _build_index(dim, n)
            index.add(vecs)

            idx_path = _index_path(document_id)
            faiss.write_index(index, str(idx_path))
            _save_id_map(document_id, chunk_ids)

            _index_cache[document_id] = index
            _id_map_cache[document_id] = list(chunk_ids)

            logger.info(
                "FAISS index built for document %s: %d vectors, dim=%d, type=%s",
                document_id, n, dim, type(index).__name__,
            )
            return True
        except Exception:
            logger.exception("Failed to build FAISS index for document %s", document_id)
            return False


def _load_index(document_id: str) -> bool:
    """Load a persisted index into cache. Must be called under _lock."""
    faiss = _import_faiss()
    if faiss is None:
        return False
    idx_path = _index_path(document_id)
    if not idx_path.exists():
        return False
    id_map = _load_id_map(document_id)
    if id_map is None:
        return False
    try:
        index = faiss.read_index(str(idx_path))
        if index.ntotal != len(id_map):
            logger.warning(
                "FAISS index/id_map size mismatch for %s (%d vs %d) — rebuilding needed",
                document_id, index.ntotal, len(id_map),
            )
            return False
        _index_cache[document_id] = index
        _id_map_cache[document_id] = id_map
        return True
    except Exception:
        logger.exception("Failed to load FAISS index for %s", document_id)
        return False


def search_document(
    document_id: str,
    query_vector: np.ndarray,
    top_k: int = 10,
) -> Optional[List[Tuple[str, float]]]:
    """Search the FAISS index for a document, returning (chunk_id, score) pairs.

    Args:
        document_id: Document whose index to search.
        query_vector: (dim,) float32 L2-normalized query embedding.
        top_k: Number of nearest neighbors to retrieve.

    Returns:
        List of (chunk_id, similarity_score) sorted descending by score,
        or None if no index is available for this document.
    """
    s = get_settings()
    if not s.faiss_enabled or not faiss_available():
        return None

    with _lock:
        if document_id not in _index_cache:
            if not _load_index(document_id):
                return None

        index = _index_cache[document_id]
        id_map = _id_map_cache[document_id]

    q = np.ascontiguousarray(query_vector.reshape(1, -1), dtype=np.float32)
    k = min(top_k, index.ntotal)
    if k == 0:
        return []

    distances, indices = index.search(q, k)

    results: List[Tuple[str, float]] = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(id_map):
            continue
        results.append((id_map[idx], float(dist)))

    return results


def search_multi_document(
    document_ids: List[str],
    query_vector: np.ndarray,
    top_k: int = 10,
) -> List[Tuple[str, float]]:
    """Search FAISS indexes across multiple documents, merging results.

    Returns top_k (chunk_id, score) pairs sorted descending by score.
    """
    all_results: List[Tuple[str, float]] = []
    for doc_id in document_ids:
        doc_results = search_document(doc_id, query_vector, top_k=top_k)
        if doc_results:
            all_results.extend(doc_results)

    all_results.sort(key=lambda x: -x[1])
    return all_results[:top_k]


def remove_document_index(document_id: str) -> None:
    """Remove a document's FAISS index from disk and cache."""
    with _lock:
        _index_cache.pop(document_id, None)
        _id_map_cache.pop(document_id, None)

    for path in (_index_path(document_id), _id_map_path(document_id)):
        try:
            if path.exists():
                os.remove(path)
        except OSError:
            logger.warning("Failed to remove %s", path)


def get_index_stats(document_id: str) -> Optional[Dict]:
    """Return stats about a document's FAISS index, or None if unavailable."""
    with _lock:
        if document_id not in _index_cache:
            if not _load_index(document_id):
                return None
        index = _index_cache[document_id]

    return {
        "document_id": document_id,
        "total_vectors": index.ntotal,
        "index_type": type(index).__name__,
        "is_trained": index.is_trained,
    }
