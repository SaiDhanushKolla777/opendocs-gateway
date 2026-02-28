"""vLLM OpenAI-compatible client (single endpoint)."""
from __future__ import annotations

import os
from typing import AsyncIterator, Dict, List

from openai import AsyncOpenAI

from app.config import get_settings
from app.services.metrics_service import record_tokens


def get_llm_client() -> AsyncOpenAI:
    s = get_settings()
    return AsyncOpenAI(
        base_url=s.vllm_base_url,
        api_key=s.vllm_api_key or os.environ.get("OPENAI_API_KEY") or "not-needed",
    )


async def chat_completion(
    messages: List[Dict[str, str]],
    max_tokens: int = 1024,
    temperature: float = 0.2,
) -> str:
    s = get_settings()
    model = s.vllm_model or "default"
    client = get_llm_client()
    resp = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if resp.usage:
        record_tokens(
            input_tokens=resp.usage.prompt_tokens or 0,
            output_tokens=resp.usage.completion_tokens or 0,
        )
    if not resp.choices:
        return ""
    return (resp.choices[0].message.content or "").strip()


async def chat_completion_stream(
    messages: List[Dict[str, str]],
    max_tokens: int = 1024,
    temperature: float = 0.2,
) -> AsyncIterator[str]:
    s = get_settings()
    model = s.vllm_model or "default"
    client = get_llm_client()
    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
    )
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
