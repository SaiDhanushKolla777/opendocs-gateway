"""Ask (Q&A) endpoints: single-doc and multi-doc with adaptive conversation."""
from __future__ import annotations

import re
from typing import List, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.dependencies import get_db_gen
from app.models import AskRequest, AskResponse, AskMultiRequest, AskMultiResponse
from app.db.repositories import get_document
from app.services.ingestion_service import document_to_chunks
from app.services.retrieval_service import (
    score_chunks,
    select_top_chunks,
    expand_with_neighbors,
    rerank_by_answer,
    format_context_with_labels,
    chunks_to_citations,
)
from app.services.llm_service import chat_completion
from app.services.metrics_service import LatencyTimer
from app.utils.prompting import SYSTEM_GROUNDED, SYSTEM_CONVERSATIONAL, build_qa_prompt
from app.utils.token_budget import truncate_to_char_budget

router = APIRouter(tags=["ask"])

MAX_HISTORY_TURNS = 8


# ---------------------------------------------------------------------------
# Intent classification — adaptive, not pattern-matched
# ---------------------------------------------------------------------------

# Action/question words that signal a REAL request (never conversational).
_ACTION_WORDS = frozenset({
    "explain", "describe", "summarize", "summary", "tell", "list", "show",
    "compare", "contrast", "analyze", "define", "clarify", "elaborate",
    "detail", "details", "discuss", "outline", "review", "identify",
    "highlight", "extract", "find", "search", "what", "why", "how",
    "when", "where", "who", "which", "does", "document", "book", "text",
    "novel", "story", "chapter", "section", "page", "author", "theme",
    "character", "plot", "design", "concept", "idea", "method", "process",
    "example", "examples", "difference", "differences", "relationship",
    "meaning", "purpose", "impact", "effect", "cause", "reason",
    "conclusion", "argument", "evidence", "claim", "opinion", "main",
    "key", "important", "significant", "major", "central", "about",
})

# Only these truly empty conversational words trigger the no-retrieval path.
_CHATTER_ONLY = frozenset({
    "thanks", "thank", "ok", "okay", "yes", "no", "yep", "nope", "sure",
    "alright", "cool", "nice", "great", "good", "fine", "got", "it",
    "understood", "right", "hm", "hmm", "hmmm", "ah", "oh", "wow",
    "lol", "haha", "bye", "hi", "hello", "hey", "lgtm", "noted",
})


def _has_intent(text: str) -> bool:
    """True if the message contains any action/question word."""
    words = set(re.findall(r"[a-zA-Z']+", text.lower()))
    return bool(words & _ACTION_WORDS)


def _is_pure_chatter(text: str) -> bool:
    """True if every word in the message is conversational filler."""
    words = re.findall(r"[a-zA-Z']+", text.lower())
    if not words:
        return True
    return all(w in _CHATTER_ONLY or len(w) <= 1 for w in words)


def _classify_intent(question: str, history: list | None) -> str:
    """Classify user message intent adaptively.

    Returns one of:
      "conversational" — greeting, thanks, acknowledgment (no retrieval needed)
      "follow_up"      — references prior conversation, wants more/different info
      "new_question"   — standalone question needing full retrieval
    """
    clean = question.strip()
    words = re.findall(r"[a-zA-Z']+", clean.lower())

    if not words:
        return "conversational"

    # If message contains ANY action/question word → never conversational
    if _has_intent(clean):
        if history and len(history) >= 2 and len(words) <= 12:
            return "follow_up"
        return "new_question"

    # Pure chatter with no action words → conversational
    if _is_pure_chatter(clean):
        return "conversational"

    # Short message with no action words but has SOME content → follow_up if history
    if history and len(history) >= 2 and len(words) <= 8:
        return "follow_up"

    return "new_question"


# ---------------------------------------------------------------------------
# Search query building — history-aware, noise-filtered
# ---------------------------------------------------------------------------

def _build_search_query(question: str, history: list | None, intent: str) -> str:
    """Build an effective search query based on intent.

    For follow-ups: enriches with prior user questions so retrieval
    covers what the user has been asking about.
    For new questions: uses the question directly.
    """
    if intent == "conversational" or not history:
        return question

    substantive_history = [
        m.content for m in history[-6:]
        if m.role == "user" and _has_intent(m.content)
    ]

    if intent == "follow_up" and substantive_history:
        return " ".join(substantive_history[-2:]) + " " + question

    if substantive_history:
        return question + " " + " ".join(substantive_history[-1:])

    return question


# ---------------------------------------------------------------------------
# Message list building — includes history for conversation continuity
# ---------------------------------------------------------------------------

def _build_messages(
    system: str,
    user_prompt: str,
    history: list | None,
) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = [{"role": "system", "content": system}]
    if history:
        for msg in history[-MAX_HISTORY_TURNS:]:
            messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_prompt})
    return messages


# ---------------------------------------------------------------------------
# Conversational path — no retrieval, just natural response with history
# ---------------------------------------------------------------------------

async def _handle_conversational(question: str, history: list | None) -> str:
    """Let the LLM respond naturally to conversational messages using history."""
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_CONVERSATIONAL},
    ]
    if history:
        for msg in history[-MAX_HISTORY_TURNS:]:
            messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": question})
    return await chat_completion(messages, max_tokens=100, temperature=0.5)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/documents/{document_id}/ask", response_model=AskResponse)
async def ask(
    document_id: str,
    body: AskRequest,
    db: Session = Depends(get_db_gen),
):
    intent = _classify_intent(body.question, body.history)

    if intent == "conversational":
        reply = await _handle_conversational(body.question, body.history)
        return AskResponse(
            answer=reply, citations=[], confidence_signal="high",
            insufficient_evidence=False,
        )

    doc = get_document(db, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    all_chunks = document_to_chunks(db, document_id)
    if not all_chunks:
        raise HTTPException(400, "Document has no chunks (ingestion may have failed)")
    s = get_settings()
    max_cite = min(body.max_citations or s.max_retrieved_chunks, s.max_retrieved_chunks)

    search_query = _build_search_query(body.question, body.history, intent)
    scored = score_chunks(search_query, all_chunks)
    selected = select_top_chunks(scored, max_cite)

    context_chunks = expand_with_neighbors(selected, all_chunks, window=1)
    context = format_context_with_labels(context_chunks)
    context = truncate_to_char_budget(context, s.max_context_chars)

    user_prompt = build_qa_prompt(context, body.question, body.answer_mode, intent)
    messages = _build_messages(SYSTEM_GROUNDED, user_prompt, body.history)

    with LatencyTimer():
        answer_text = await chat_completion(
            messages, max_tokens=s.max_answer_tokens, temperature=0.2,
        )

    best_cites = rerank_by_answer(context_chunks, answer_text, top_k=max_cite)
    citations = chunks_to_citations(best_cites)
    insufficient = (
        "insufficient evidence" in answer_text.lower()
        or "not contain" in answer_text.lower()
    )
    return AskResponse(
        answer=answer_text, citations=citations,
        confidence_signal="low" if insufficient else "medium",
        insufficient_evidence=insufficient,
    )


@router.post("/documents/ask-multi", response_model=AskMultiResponse)
async def ask_multi(
    body: AskMultiRequest,
    db: Session = Depends(get_db_gen),
):
    intent = _classify_intent(body.question, body.history)

    if intent == "conversational":
        reply = await _handle_conversational(body.question, body.history)
        return AskMultiResponse(
            answer=reply, citations=[], insufficient_evidence=False,
        )

    s = get_settings()
    if len(body.document_ids) > s.max_multi_docs:
        raise HTTPException(400, f"At most {s.max_multi_docs} documents allowed")

    chunks_by_doc: dict[str, list] = {}
    all_chunks = []
    for doc_id in body.document_ids:
        doc = get_document(db, doc_id)
        if not doc:
            raise HTTPException(404, f"Document not found: {doc_id}")
        doc_chunks = document_to_chunks(db, doc_id)
        chunks_by_doc[doc_id] = doc_chunks
        all_chunks.extend(doc_chunks)
    if not all_chunks:
        raise HTTPException(400, "No chunks found for the selected documents")

    num_docs = len(body.document_ids)
    per_doc = max(2, s.max_retrieved_chunks // num_docs)

    search_query = _build_search_query(body.question, body.history, intent)
    selected = []
    for doc_id in body.document_ids:
        doc_chunks = chunks_by_doc[doc_id]
        scored = score_chunks(search_query, doc_chunks)
        top = select_top_chunks(scored, per_doc)
        selected.extend(top)

    context_chunks = expand_with_neighbors(selected, all_chunks, window=1)
    context = format_context_with_labels(context_chunks)
    context = truncate_to_char_budget(context, s.max_context_chars)

    user_prompt = build_qa_prompt(context, body.question, body.answer_mode, intent)
    messages = _build_messages(SYSTEM_GROUNDED, user_prompt, body.history)

    with LatencyTimer():
        answer_text = await chat_completion(
            messages, max_tokens=s.max_answer_tokens, temperature=0.2,
        )

    best_cites = rerank_by_answer(context_chunks, answer_text, top_k=s.max_retrieved_chunks)
    citations = chunks_to_citations(best_cites)
    insufficient = "insufficient evidence" in answer_text.lower()
    return AskMultiResponse(
        answer=answer_text, citations=citations,
        insufficient_evidence=insufficient,
    )
