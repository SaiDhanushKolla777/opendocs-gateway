"""Retrieval: chunk scoring, context assembly, citation building (v1.1 improved)."""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import List, Tuple

from app.models import Citation, Chunk

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


def score_chunks(query: str, chunks: List[Chunk]) -> List[Tuple[Chunk, float]]:
    """Score chunks using TF-IDF-like weighting with proper noun boosting."""
    terms, important_terms = _extract_query_terms(query)

    if not terms and not important_terms:
        return [(c, 0.0) for c in chunks]

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

    scored: List[Tuple[Chunk, float]] = []
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

        scored.append((c, score))

    scored.sort(key=lambda x: -x[1])
    return scored


def _make_bigrams(terms: List[str]) -> List[str]:
    if len(terms) < 2:
        return []
    return [f"{terms[i]} {terms[i+1]}" for i in range(len(terms) - 1)]


def select_top_chunks(
    scored: List[Tuple[Chunk, float]],
    max_chunks: int,
    min_score: float = 0.01,
) -> List[Chunk]:
    """Select top-scoring chunks, filtering near-zero scores."""
    if not scored:
        return []
    top_score = scored[0][1] if scored else 0
    threshold = max(min_score, top_score * 0.15)
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
        answer_lower = answer.lower()
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
