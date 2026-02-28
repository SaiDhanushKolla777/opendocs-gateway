"""Prompt construction for grounded Q&A, extraction, and comparison."""
from __future__ import annotations

from app.utils.token_budget import truncate_to_char_budget

# ---------------------------------------------------------------------------
# System prompts — separated by mode
# ---------------------------------------------------------------------------

SYSTEM_GROUNDED = (
    "You are a document-grounded assistant having a conversation with the user.\n\n"
    "Rules:\n"
    "1. Answer ONLY from the provided document context. Write naturally.\n"
    "2. NEVER reference chunks, sources, labels, or context numbering — citations are automatic.\n"
    "3. Use conversation history to understand follow-ups: pronouns, references to 'it', "
    "'that', 'the first one' etc. resolve against prior messages.\n"
    "4. For follow-up requests like 'more detail' or 'elaborate', provide NEW information "
    "from the context that you haven't mentioned yet. Do NOT repeat your previous answer.\n"
    "5. If the context lacks enough information, say so honestly.\n"
    "6. Match the depth to the question: short questions get concise answers, "
    "detailed questions get thorough answers."
)

SYSTEM_CONVERSATIONAL = (
    "You are a helpful document assistant. The user may send conversational remarks "
    "like 'thanks', 'ok', 'got it', or brief reactions. Respond naturally and briefly "
    "(1-2 sentences max). Be warm but concise. If the user seems to be asking a follow-up, "
    "let them know you're ready to help."
)

# Also exported under the old name for backward compatibility
SYSTEM_PREFIX = SYSTEM_GROUNDED


# ---------------------------------------------------------------------------
# Q&A prompt — intent-aware
# ---------------------------------------------------------------------------

_MODE_INSTRUCTIONS = {
    "plain_english": "Answer in clear, plain English.",
    "concise_bullets": "Answer with concise bullet points.",
    "policy_legal": "Answer in a formal, policy/legal tone.",
    "student_friendly": "Summarize in a student-friendly way.",
    "executive_summary": "Provide an executive summary.",
}

_FOLLOW_UP_HINT = (
    " This is a follow-up question. Build on what you previously discussed — "
    "add new details, don't repeat the same information."
)


def build_qa_prompt(
    context: str,
    question: str,
    answer_mode: str = "plain_english",
    intent: str = "new_question",
) -> str:
    mode_inst = _MODE_INSTRUCTIONS.get(answer_mode, _MODE_INSTRUCTIONS["plain_english"])
    follow_up = _FOLLOW_UP_HINT if intent == "follow_up" else ""
    return (
        f"Context from the document(s):\n\n"
        f"{truncate_to_char_budget(context, 28000)}\n\n"
        f"Question: {question}\n\n"
        f"{mode_inst}{follow_up} "
        f"Do not mention chunks, sources, or context labels in your answer."
    )


# ---------------------------------------------------------------------------
# Extraction prompt
# ---------------------------------------------------------------------------

def build_extraction_prompt(context: str, schema_description: str) -> str:
    return (
        "Extract structured information from the following document context. "
        "Return valid JSON only.\n\n"
        f"Context:\n\n{truncate_to_char_budget(context, 24000)}\n\n"
        f"Schema/instructions: {schema_description}\n\n"
        "Output valid JSON with the requested fields. "
        "Do not include any text outside the JSON."
    )


# ---------------------------------------------------------------------------
# Comparison prompt
# ---------------------------------------------------------------------------

def build_compare_prompt(
    old_context: str,
    new_context: str,
    max_chars_each: int = 12000,
) -> str:
    old_trunc = truncate_to_char_budget(old_context, max_chars_each)
    new_trunc = truncate_to_char_budget(new_context, max_chars_each)
    return (
        "Compare the OLD and NEW document excerpts below. "
        "Summarize: what changed, what was added, what was removed.\n\n"
        f"OLD document:\n{old_trunc}\n\n"
        f"NEW document:\n{new_trunc}\n\n"
        "Be concise."
    )
