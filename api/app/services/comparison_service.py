"""Document comparison: adaptive for version diffs and cross-document analysis."""
from __future__ import annotations

import json
import re
from typing import List

from app.models import Chunk, Citation
from app.services.llm_service import chat_completion
from app.services.retrieval_service import format_context_with_labels, _clean_snippet
from app.config import get_settings


def _sample_spread(chunks: List[Chunk], n: int) -> List[Chunk]:
    if len(chunks) <= n:
        return chunks
    step = len(chunks) / n
    return [chunks[int(i * step)] for i in range(n)]


def _text_fingerprint(chunks: List[Chunk], sample: int = 10) -> str:
    """Create a rough fingerprint from evenly sampled chunks for identity check."""
    sampled = _sample_spread(chunks, sample)
    return "\n".join(c.text[:100].strip().lower() for c in sampled)


def _detect_comparison_mode(
    old_chunks: List[Chunk],
    new_chunks: List[Chunk],
) -> str:
    """Determine the nature of the comparison.

    Returns:
      "identical"  — same content
      "version"    — same document, different versions (shared title or high overlap)
      "different"  — entirely different documents
    """
    old_fp = _text_fingerprint(old_chunks)
    new_fp = _text_fingerprint(new_chunks)

    if old_fp == new_fp:
        return "identical"

    old_title = old_chunks[0].document_title if old_chunks else ""
    new_title = new_chunks[0].document_title if new_chunks else ""

    if old_title and new_title:
        old_base = re.sub(r"\.\w+$", "", old_title).lower().strip()
        new_base = re.sub(r"\.\w+$", "", new_title).lower().strip()
        if old_base == new_base:
            return "version"

    old_words = set(old_fp.split())
    new_words = set(new_fp.split())
    if old_words and new_words:
        overlap = len(old_words & new_words) / max(len(old_words | new_words), 1)
        if overlap > 0.5:
            return "version"

    return "different"


# ---------------------------------------------------------------------------
# Prompts — adapt based on comparison mode
# ---------------------------------------------------------------------------

_SYSTEM = "You compare documents and output ONLY valid JSON. No markdown fences, no explanation text."

_VERSION_PROMPT = """These are two versions of the SAME document. Identify specific changes between them.

OLD VERSION:
{old_ctx}

NEW VERSION:
{new_ctx}

Return JSON with:
- "verdict": one of "identical", "minor_changes", "significant_changes"
- "summary": 2-3 sentences describing what changed
- "additions": list of short descriptions (1 sentence each) of content added
- "removals": list of short descriptions (1 sentence each) of content removed
- "modifications": list of {{"section": "short name", "change": "1 sentence"}}
- "key_differences": 3-5 most important changes as concise strings

Keep every item to 1-2 sentences. Summarize, don't paste raw text."""

_DIFFERENT_PROMPT = """These are TWO DIFFERENT documents. Compare their content, scope, and purpose.

DOCUMENT A:
{old_ctx}

DOCUMENT B:
{new_ctx}

Return JSON with:
- "verdict": "completely_different"
- "summary": 2-3 sentences describing what each document is about and how they differ
- "doc_a_about": 1-2 sentence description of Document A
- "doc_b_about": 1-2 sentence description of Document B
- "key_differences": 3-5 concise strings highlighting the main differences in content, purpose, audience, or style
- "commonalities": list of any shared themes or topics (can be empty)
- "additions": [] (empty — not applicable for different documents)
- "removals": [] (empty — not applicable for different documents)
- "modifications": [] (empty — not applicable for different documents)

Be concise."""


async def compare_documents(
    old_chunks: List[Chunk],
    new_chunks: List[Chunk],
) -> tuple[str, dict, List[Citation], List[Citation]]:
    mode = _detect_comparison_mode(old_chunks, new_chunks)

    # Fast path: identical documents
    if mode == "identical":
        structured = {
            "verdict": "identical",
            "additions": [],
            "removals": [],
            "modifications": [],
            "key_differences": [],
        }
        return (
            "These documents are identical — no differences found.",
            structured,
            _build_citations(old_chunks, 2),
            _build_citations(new_chunks, 2),
        )

    s = get_settings()
    old_sample = _sample_spread(old_chunks, 8)
    new_sample = _sample_spread(new_chunks, 8)

    old_ctx = format_context_with_labels(old_sample, "Old" if mode == "version" else "DocA")
    new_ctx = format_context_with_labels(new_sample, "New" if mode == "version" else "DocB")

    from app.utils.token_budget import truncate_to_char_budget
    budget = s.max_compare_context_chars
    old_ctx = truncate_to_char_budget(old_ctx, budget // 2)
    new_ctx = truncate_to_char_budget(new_ctx, budget // 2)

    template = _VERSION_PROMPT if mode == "version" else _DIFFERENT_PROMPT
    user_prompt = template.format(old_ctx=old_ctx, new_ctx=new_ctx)
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user_prompt},
    ]

    raw = await chat_completion(messages, max_tokens=s.max_answer_tokens, temperature=0.1)
    result = _parse_compare_json(raw)
    summary = result.get("summary", raw)

    structured = {
        "verdict": result.get("verdict", "unknown"),
        "additions": result.get("additions", []),
        "removals": result.get("removals", []),
        "modifications": result.get("modifications", []),
        "key_differences": result.get("key_differences", []),
    }

    if mode == "different":
        structured["doc_a_about"] = result.get("doc_a_about", "")
        structured["doc_b_about"] = result.get("doc_b_about", "")
        structured["commonalities"] = result.get("commonalities", [])

    return (
        summary,
        structured,
        _build_citations(old_sample, 3),
        _build_citations(new_sample, 3),
    )


def _build_citations(chunks: List[Chunk], n: int) -> List[Citation]:
    return [
        Citation(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            document_title=c.document_title,
            snippet=_clean_snippet(c.text),
            page_number=c.page_number,
        )
        for c in chunks[:n]
    ]


def _parse_compare_json(text: str) -> dict:
    text = text.strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"summary": text}
