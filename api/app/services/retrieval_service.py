"""Retrieval: hybrid RAG (dense embeddings + FAISS ANN) + TF-IDF fusion, context assembly, citations."""
from __future__ import annotations

import logging
import math
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

from app.config import get_settings
from app.models import Citation, Chunk
from app.services.embedding_service import (
    embedding_available,
    encode_query,
    semantic_similarity_scores,
)

logger = logging.getLogger(__name__)

STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to",
    "of", "and", "or", "it", "its", "this", "that", "for", "with", "as",
    "by", "from", "be", "has", "had", "have", "do", "does", "did", "not",
    "but", "what", "who", "how", "when", "where", "which", "about", "i",
    "me", "my", "you", "your", "we", "our", "they", "them", "their", "he",
    "she", "him", "her", "so", "if", "then", "than", "no", "yes", "can",
    "will", "would", "could", "should", "may", "might", "shall", "must",
    "also", "very", "too", "just", "more", "most", "some", "any", "all",
    "each", "every", "both", "few", "many", "much", "such", "own", "other",
    "over", "into", "out", "up", "down", "been", "being", "there", "here",
    "only", "well", "even", "still", "quite", "rather", "yet", "ever",
    "never", "always", "often", "sometimes", "cite", "key", "describe",
    "explain", "novel", "story", "book", "course", "tell",
})


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z']+", text.lower())


def _extract_query_terms(query: str) -> Tuple[List[str], List[str]]:
    """Extract regular terms and important terms (capitalized/proper nouns) from query."""
    tokens = _tokenize(query)
    terms = [t for t in tokens if t not in STOP_WORDS and len(t) > 1]

    raw_words = re.findall(r"\b[A-Z][a-z]+\b", query)
    important = [w.lower() for w in raw_words if w.lower() not in STOP_WORDS]

    if not terms:
        terms = [t for t in tokens if len(t) > 1]

    return terms, important


def tfidf_scores_parallel(query: str, chunks: List[Chunk]) -> List[float]:
    """One TF-IDF-style score per chunk (same order as ``chunks``)."""
    terms, important_terms = _extract_query_terms(query)
    if not chunks:
        return []

    if not terms and not important_terms:
        return [0.0] * len(chunks)

    num_chunks = len(chunks)
    doc_freq: Counter = Counter()
    for c in chunks:
        text_lower = c.text.lower()
        for t in set(terms + important_terms):
            if t in text_lower:
                doc_freq[t] += 1

    idf = {}
    for t in set(terms + important_terms):
        df = doc_freq.get(t, 0)
        idf[t] = math.log((num_chunks + 1) / (df + 1)) + 1.0

    scores: List[float] = []
    for c in chunks:
        text_lower = c.text.lower()
        text_tokens = _tokenize(c.text)
        token_count = len(text_tokens) or 1

        score = 0.0

        for t in terms:
            tf = text_lower.count(t) / token_count
            score += tf * idf.get(t, 1.0)

        for t in important_terms:
            tf = text_lower.count(t) / token_count
            score += tf * idf.get(t, 1.0) * 2.5

        bigrams_query = _make_bigrams(terms + important_terms)
        if bigrams_query:
            for b in bigrams_query:
                if b in text_lower:
                    score += 1.5

        scores.append(score)

    return scores


def _make_bigrams(terms: List[str]) -> List[str]:
    if len(terms) < 2:
        return []
    return [f"{terms[i]} {terms[i+1]}" for i in range(len(terms) - 1)]


def _rank_map_from_scores(chunks: List[Chunk], scores: List[float]) -> Dict[str, int]:
    """1-based rank (1 = best) for each chunk_id."""
    order = sorted(range(len(chunks)), key=lambda i: -scores[i])
    return {chunks[idx].chunk_id: pos + 1 for pos, idx in enumerate(order)}


def _min_max_norm(scores: List[float]) -> List[float]:
    if not scores:
        return []
    lo, hi = min(scores), max(scores)
    if hi - lo < 1e-12:
        return [1.0] * len(scores)
    return [(x - lo) / (hi - lo) for x in scores]


def _hybrid_rrf(
    chunks: List[Chunk],
    tfidf_scores: List[float],
    sem_scores: List[float],
    k: int,
) -> List[Tuple[Chunk, float]]:
    """Reciprocal Rank Fusion: robust merge of lexical and semantic rankings."""
    r_tfidf = _rank_map_from_scores(chunks, tfidf_scores)
    r_sem = _rank_map_from_scores(chunks, sem_scores)
    fused: List[Tuple[Chunk, float]] = []
    for c in chunks:
        cid = c.chunk_id
        fused.append(
            (
                c,
                1.0 / (k + r_tfidf[cid]) + 1.0 / (k + r_sem[cid]),
            )
        )
    fused.sort(key=lambda x: -x[1])
    return fused


def _hybrid_weighted(
    chunks: List[Chunk],
    tfidf_scores: List[float],
    sem_scores: List[float],
    w_sem: float,
    w_tfidf: float,
) -> List[Tuple[Chunk, float]]:
    """Min–max normalize both signals and blend (complements RRF)."""
    n_t = _min_max_norm(tfidf_scores)
    n_s = _min_max_norm(sem_scores)
    w = w_sem + w_tfidf
    a = (w_sem / w) if w > 0 else 0.5
    b = (w_tfidf / w) if w > 0 else 0.5
    fused = [
        (chunks[i], a * n_s[i] + b * n_t[i])
        for i in range(len(chunks))
    ]
    fused.sort(key=lambda x: -x[1])
    return fused


def _faiss_semantic_scores(
    query: str,
    chunks: List[Chunk],
) -> Optional[List[float]]:
    """Use FAISS ANN index to compute semantic similarity scores.

    Returns a list of scores aligned with ``chunks`` (same order), or None
    if FAISS is unavailable or no index exists for the relevant documents.
    """
    try:
        from app.services.faiss_index import faiss_available, search_document
    except ImportError:
        return None

    s = get_settings()
    if not s.faiss_enabled or not faiss_available():
        return None

    doc_ids = list({c.document_id for c in chunks})

    try:
        q_vec = encode_query(query)
    except Exception:
        return None

    faiss_hits: Dict[str, float] = {}
    for doc_id in doc_ids:
        results = search_document(doc_id, q_vec, top_k=len(chunks))
        if results is None:
            return None
        for chunk_id, score in results:
            faiss_hits[chunk_id] = score

    scores: List[float] = []
    for c in chunks:
        scores.append(faiss_hits.get(c.chunk_id, -1.0))
    return scores


def score_chunks(query: str, chunks: List[Chunk]) -> List[Tuple[Chunk, float]]:
    """Hybrid RAG + TF-IDF when enabled and embeddings exist; else TF-IDF only.

    When FAISS is available, uses ANN index for fast semantic search instead of
    brute-force dot products. Falls back to brute-force or TF-IDF-only as needed.
    Uses reciprocal rank fusion (default) or weighted blend of normalized scores.
    """
    s = get_settings()
    tfidf = tfidf_scores_parallel(query, chunks)
    if not chunks:
        return []

    use_rag = (
        s.rag_enabled
        and embedding_available()
        and all(c.embedding is not None for c in chunks)
    )

    if not use_rag:
        scored = list(zip(chunks, tfidf))
        scored.sort(key=lambda x: -x[1])
        return scored

    sem = None
    if s.faiss_enabled:
        try:
            sem = _faiss_semantic_scores(query, chunks)
            if sem is not None:
                logger.debug("Using FAISS ANN for semantic scoring (%d chunks)", len(chunks))
        except Exception as e:
            logger.debug("FAISS scoring unavailable, falling back: %s", e)
            sem = None

    if sem is None:
        try:
            sem = semantic_similarity_scores(query, chunks)
        except Exception as e:
            logger.warning("Semantic scoring failed; using TF-IDF only: %s", e)
            scored = list(zip(chunks, tfidf))
            scored.sort(key=lambda x: -x[1])
            return scored

    mode = (s.rag_fusion_mode or "rrf").strip().lower()
    if mode == "weighted":
        return _hybrid_weighted(
            chunks, tfidf, sem,
            s.rag_semantic_weight, s.rag_tfidf_weight,
        )
    return _hybrid_rrf(chunks, tfidf, sem, s.rrf_k)


def select_top_chunks(
    scored: List[Tuple[Chunk, float]],
    max_chunks: int,
    min_score: float = 0.01,
) -> List[Chunk]:
    """Select top-scoring chunks, filtering near-zero scores.

    RRF scores are small (~0.03); TF-IDF scores are often larger. Use a relative
    cutoff for small magnitudes and keep the legacy absolute floor for strong
    lexical scores only.
    """
    if not scored:
        return []
    top_score = scored[0][1]
    rel = abs(top_score) * 0.15
    if abs(top_score) >= 0.25:
        threshold = max(min_score, rel)
    else:
        threshold = max(rel, 1e-12)
    selected = [c for c, s in scored if s >= threshold][:max_chunks]
    if not selected and scored:
        selected = [scored[0][0]]
    return selected


def _clean_snippet(text: str, max_len: int = 200) -> str:
    """Extract a clean snippet starting at a sentence boundary."""
    text = text.strip()
    if not text:
        return ""
    match = re.search(r'(?:^|[.!?]\s+)([A-Z])', text)
    if match and match.start() > 0:
        text = text[match.start():].lstrip('. !?')

    if len(text) <= max_len:
        return text

    cut = text[:max_len]
    last_period = max(cut.rfind('. '), cut.rfind('." '), cut.rfind('.\n'))
    if last_period > max_len // 3:
        return cut[:last_period + 1]
    last_space = cut.rfind(' ')
    if last_space > max_len // 2:
        return cut[:last_space] + '…'
    return cut + '…'


def chunks_to_citations(chunks: List[Chunk]) -> List[Citation]:
    """Build citation list with clean snippets."""
    return [
        Citation(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            document_title=c.document_title,
            snippet=_clean_snippet(c.text),
            page_number=c.page_number,
        )
        for c in chunks
    ]


def expand_with_neighbors(
    selected: List[Chunk],
    all_chunks: List[Chunk],
    window: int = 1,
) -> List[Chunk]:
    """Expand selected chunks to include neighboring chunks for richer context."""
    by_doc: dict[str, dict[int, Chunk]] = {}
    for c in all_chunks:
        by_doc.setdefault(c.document_id, {})[c.chunk_index] = c

    seen: set[str] = set()
    expanded: List[Chunk] = []
    for c in selected:
        doc_chunks = by_doc.get(c.document_id, {})
        for offset in range(-window, window + 1):
            neighbor = doc_chunks.get(c.chunk_index + offset)
            if neighbor and neighbor.chunk_id not in seen:
                seen.add(neighbor.chunk_id)
                expanded.append(neighbor)

    expanded.sort(key=lambda c: (c.document_id, c.chunk_index))
    return expanded


def rerank_by_answer(chunks: List[Chunk], answer: str, top_k: int = 6) -> List[Chunk]:
    """Re-rank chunks by overlap with the generated answer text."""
    answer_tokens = set(_tokenize(answer)) - STOP_WORDS
    if not answer_tokens:
        return chunks[:top_k]

    scored: List[Tuple[Chunk, float]] = []
    for c in chunks:
        chunk_tokens = set(_tokenize(c.text))
        overlap = len(answer_tokens & chunk_tokens)
        unique_overlap = len((answer_tokens & chunk_tokens) - STOP_WORDS)
        phrase_bonus = 0.0
        words = list(answer_tokens)[:20]
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            if bigram in c.text.lower():
                phrase_bonus += 1.0
        scored.append((c, unique_overlap + phrase_bonus))

    scored.sort(key=lambda x: -x[1])
    return [c for c, _ in scored[:top_k]]


def format_context_with_labels(chunks: List[Chunk], prefix: str = "Chunk") -> str:
    """Format chunks as labeled context for the prompt."""
    parts = []
    for i, c in enumerate(chunks, 1):
        label = f"[{prefix} {i}]"
        parts.append(f"{label} (doc: {c.document_title})\n{c.text}")
    return "\n\n".join(parts)
