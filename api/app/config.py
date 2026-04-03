"""Centralized configuration for OpenDocs Gateway (single-GPU MI300X)."""
from __future__ import annotations

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment."""

    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    frontend_port: int = Field(default=3000, alias="FRONTEND_PORT")

    # vLLM endpoint (OpenAI-compatible)
    vllm_base_url: str = Field(default="http://localhost:8001/v1", alias="VLLM_BASE_URL")
    vllm_model: str = Field(default="", alias="VLLM_MODEL")
    vllm_api_key: Optional[str] = Field(default=None, alias="VLLM_API_KEY")

    database_url: str = Field(default="sqlite:///./data/opendocs.db", alias="DATABASE_URL")
    redis_url: Optional[str] = Field(default=None, alias="REDIS_URL")

    upload_dir: str = Field(default="./data/uploads", alias="UPLOAD_DIR")
    data_dir: str = Field(default="./data", alias="DATA_DIR")
    max_upload_mb: int = Field(default=50, alias="MAX_UPLOAD_MB")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Context and retrieval (MI300X long-context aware)
    max_retrieved_chunks: int = Field(default=6, alias="MAX_RETRIEVED_CHUNKS")
    max_context_chars: int = Field(default=32000, alias="MAX_CONTEXT_CHARS")
    max_answer_tokens: int = Field(default=1024, alias="MAX_ANSWER_TOKENS")
    max_extraction_tokens: int = Field(default=2048, alias="MAX_EXTRACTION_TOKENS")
    max_compare_context_chars: int = Field(default=24000, alias="MAX_COMPARE_CONTEXT_CHARS")
    max_multi_docs: int = Field(default=5, alias="MAX_MULTI_DOCS")
    default_long_context_mode: bool = Field(default=False, alias="DEFAULT_LONG_CONTEXT_MODE")
    max_concurrent_requests: int = Field(default=4, alias="MAX_CONCURRENT_REQUESTS")

    # Hybrid RAG: dense embeddings + TF-IDF (reciprocal rank fusion or weighted blend)
    rag_enabled: bool = Field(default=True, alias="RAG_ENABLED")
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL",
    )
    rag_fusion_mode: str = Field(default="rrf", alias="RAG_FUSION_MODE")  # "rrf" | "weighted"
    rag_semantic_weight: float = Field(default=0.55, alias="RAG_SEMANTIC_WEIGHT")
    rag_tfidf_weight: float = Field(default=0.45, alias="RAG_TFIDF_WEIGHT")
    rrf_k: int = Field(default=60, alias="RRF_K")

    model_config = {"env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    """Return application settings singleton."""
    return Settings()
