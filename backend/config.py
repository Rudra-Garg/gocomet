from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str = "gemini-3.1-flash-lite"
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_base_url: str = "https://cloud.langfuse.com"
    db_path: str = "trade_validation.db"
    checkpoint_db_path: str = "trade_validation_checkpoints.db"
    max_retries: int = 3
    confidence_threshold: float = 0.5
    max_tokens_per_run: int = 10000
    imap_host: str | None = None
    imap_port: int = 993
    imap_username: str | None = None
    imap_password: str | None = None
    imap_mailbox: str = "INBOX"
    imap_poll_seconds: int = 60
    smtp_host: str | None = None
    smtp_port: int = 465
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None


def get_settings(require_gemini: bool = True) -> Settings:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if require_gemini and not api_key:
        raise RuntimeError("GEMINI_API_KEY is required")

    return Settings(
        gemini_api_key=api_key,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY") or None,
        langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY") or None,
        langfuse_base_url=os.getenv(
            "LANGFUSE_BASE_URL",
            os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        ),
        db_path=os.getenv("DB_PATH", "trade_validation.db"),
        checkpoint_db_path=os.getenv(
            "CHECKPOINT_DB_PATH",
            "trade_validation_checkpoints.db",
        ),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.5")),
        max_tokens_per_run=int(os.getenv("MAX_TOKENS_PER_RUN", "10000")),
        imap_host=os.getenv("IMAP_HOST") or None,
        imap_port=int(os.getenv("IMAP_PORT", "993")),
        imap_username=os.getenv("IMAP_USERNAME") or None,
        imap_password=os.getenv("IMAP_PASSWORD") or None,
        imap_mailbox=os.getenv("IMAP_MAILBOX", "INBOX"),
        imap_poll_seconds=int(os.getenv("IMAP_POLL_SECONDS", "60")),
        smtp_host=os.getenv("SMTP_HOST") or None,
        smtp_port=int(os.getenv("SMTP_PORT", "465")),
        smtp_username=os.getenv("SMTP_USERNAME") or None,
        smtp_password=os.getenv("SMTP_PASSWORD") or None,
        smtp_from=os.getenv("SMTP_FROM") or None,
    )
