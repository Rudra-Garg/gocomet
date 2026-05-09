from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str = "gemini-3.1-flash-lite"
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"
    db_path: str = "trade_validation.db"
    checkpoint_db_path: str = "trade_validation_checkpoints.db"
    max_retries: int = 3
    confidence_threshold: float = 0.5
    max_tokens_per_run: int = 10000


def get_settings(require_gemini: bool = True) -> Settings:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if require_gemini and not api_key:
        raise RuntimeError("GEMINI_API_KEY is required")

    return Settings(
        gemini_api_key=api_key,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY") or None,
        langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY") or None,
        langfuse_host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        db_path=os.getenv("DB_PATH", "trade_validation.db"),
        checkpoint_db_path=os.getenv(
            "CHECKPOINT_DB_PATH",
            "trade_validation_checkpoints.db",
        ),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.5")),
        max_tokens_per_run=int(os.getenv("MAX_TOKENS_PER_RUN", "10000")),
    )
