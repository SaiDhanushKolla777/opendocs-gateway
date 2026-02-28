"""Structured extraction with LLM-driven adaptive schema detection."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.models import Citation, Chunk
from app.services.llm_service import chat_completion
from app.services.retrieval_service import format_context_with_labels, _clean_snippet
from app.utils.prompting import build_extraction_prompt
from app.utils.token_budget import truncate_to_char_budget
from app.config import get_settings


def _sample_spread(chunks: List[Chunk], n: int) -> List[Chunk]:
    if len(chunks) <= n:
        return chunks
    step = len(chunks) / n
    return [chunks[int(i * step)] for i in range(n)]


DETECT_PROMPT = """Read the document excerpts below and respond with ONLY a JSON object (no markdown, no explanation) with two fields:

1. "document_type": a short label (e.g. "novel", "legal_contract", "research_paper", "technical_manual", "meeting_minutes", "financial_report", "resume", "news_article", "correspondence", "policy_document", "textbook", etc.)
2. "extraction_schema": a string describing what fields to extract from THIS SPECIFIC document. Choose 5-8 fields that capture the most valuable structured information. Be specific to the document's content — do NOT use generic business fields for a novel, or literary fields for a contract.

Examples:
- Legal contract → parties, effective_date, termination_date, obligations, payment_terms, governing_law, key_clauses
- Novel → main_characters (with name, role, arc), central_conflict, settings, themes, plot_structure, narrative_style, key_relationships
- Research paper → title, authors, abstract, methodology, key_findings, conclusions, references_count
- Technical manual → product_name, sections, procedures, safety_warnings, specifications, troubleshooting

Document excerpts:
"""


async def detect_schema(chunks: List[Chunk]) -> tuple[str, str]:
    """Use the LLM to analyze the document and generate an appropriate schema.

    Samples from beginning, middle, and end for a comprehensive view.
    """
    sampled = _sample_spread(chunks, 8)
    sample_text = "\n\n---\n\n".join(c.text for c in sampled)
    sample_text = truncate_to_char_budget(sample_text, 5000)

    messages = [
        {"role": "system", "content": "You analyze documents and output JSON only. No markdown fences, no explanation."},
        {"role": "user", "content": DETECT_PROMPT + sample_text},
    ]
    raw = await chat_completion(messages, max_tokens=500, temperature=0.1)
    data, ok = _parse_json(raw)
    if ok and "extraction_schema" in data:
        return data.get("document_type", "unknown"), data["extraction_schema"]
    return "unknown", _fallback_schema()


def _fallback_schema() -> str:
    return (
        "Extract the most important structured information from this document: "
        "key_entities (list of {name, type, description}), "
        "summary (string, 2-3 sentences), "
        "topics (list of strings), "
        "key_facts (list of strings), "
        "dates_mentioned (list of {date, context}). "
        "Use null for fields you cannot determine."
    )


async def extract_structured(
    context_chunks: List[Chunk],
    schema_description: Optional[str] = None,
    max_retries: int = 2,
) -> tuple[Dict[str, Any], List[Citation], str]:
    """Run extraction with auto-detected or user-provided schema.

    Uses broad sampling to ensure comprehensive coverage.
    """
    s = get_settings()

    if not schema_description:
        doc_type, schema_description = await detect_schema(context_chunks)

    context = format_context_with_labels(context_chunks)
    context = truncate_to_char_budget(context, 20000)

    extraction_prompt = (
        "Extract structured information from the following document context. "
        "Return valid JSON only.\n\n"
        f"Context:\n\n{context}\n\n"
        f"Schema/instructions: {schema_description}\n\n"
        "IMPORTANT: Be thorough — extract ALL instances you find in the context, "
        "not just the first few. For lists (characters, entities, events), "
        "include every one mentioned in the context. "
        "Output valid JSON with the requested fields. No text outside the JSON."
    )
    messages = [
        {"role": "system", "content": "You extract structured data from documents. Return only valid JSON, no markdown fences, no explanation text."},
        {"role": "user", "content": extraction_prompt},
    ]
    raw = await chat_completion(messages, max_tokens=s.max_extraction_tokens, temperature=0.1)

    citations = [
        Citation(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            document_title=c.document_title,
            snippet=_clean_snippet(c.text),
            page_number=c.page_number,
        )
        for c in context_chunks
    ]

    for attempt in range(max_retries):
        data, ok = _parse_json(raw)
        if ok:
            return data, citations, "valid"
        raw = await chat_completion(
            [
                {"role": "system", "content": "Fix this into valid JSON only. No explanation."},
                {"role": "user", "content": raw[:3000]},
            ],
            max_tokens=s.max_extraction_tokens,
            temperature=0.0,
        )
    data, _ = _parse_json(raw)
    return data or {}, citations, "invalid"


def _parse_json(text: str) -> tuple[Dict[str, Any], bool]:
    text = text.strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
    try:
        return json.loads(text), True
    except json.JSONDecodeError:
        return {}, False
