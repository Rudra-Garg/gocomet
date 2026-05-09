from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str = "gemini-3.1-flash-lite"
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str | None = None
    db_path: str = "trade_validation.db"
    checkpoint_db_path: str = "trade_validation_checkpoints.db"
    extraction_retry_cap: int = 3
    confidence_threshold: float = 0.75
    token_budget: int = 4096


def get_settings(require_gemini: bool = True) -> Settings:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if require_gemini and not api_key:
        raise RuntimeError("GEMINI_API_KEY is required")

    return Settings(
        gemini_api_key=api_key,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY") or None,
        langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY") or None,
        langfuse_host=os.getenv("LANGFUSE_HOST") or None,
        db_path=os.getenv("DB_PATH", "trade_validation.db"),
        checkpoint_db_path=os.getenv(
            "CHECKPOINT_DB_PATH",
            "trade_validation_checkpoints.db",
        ),
        extraction_retry_cap=int(os.getenv("EXTRACTION_RETRY_CAP", "3")),
        confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.75")),
        token_budget=int(os.getenv("TOKEN_BUDGET", "4096")),
    )

