"""Token and context budgeting for single-GPU / long-context awareness."""
from __future__ import annotations


def chars_to_tokens_approx(chars: int, chars_per_token: float = 4.0) -> int:
    """Rough character-to-token estimate."""
    return max(0, int(chars / chars_per_token))


def truncate_to_char_budget(text: str, max_chars: int) -> str:
    """Truncate text to fit character budget."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def fit_chunks_to_budget(
    chunks: list[tuple[str, str]],
    max_chars: int,
    separator: str = "\n\n",
) -> tuple[str, list[int]]:
    """
    Fit chunk texts into a character budget. Returns (concatenated_text, indices_included).
    chunks is list of (chunk_id, text).
    """
    result: list[str] = []
    indices: list[int] = []
    sep_len = len(separator)
    used = 0
    for i, (_, text) in enumerate(chunks):
        need = len(text) + (sep_len if result else 0)
        if used + need > max_chars:
            break
        if result:
            result.append(separator)
            used += sep_len
        result.append(text)
        used += len(text)
        indices.append(i)
    return "".join(result), indices
