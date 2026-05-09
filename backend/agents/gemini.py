from __future__ import annotations

import base64
from collections.abc import Sequence

from backend.config import Settings


def _client(settings: Settings):
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "google-genai is required for Gemini calls. Install requirements.txt.",
        ) from exc
    return genai.Client(api_key=settings.gemini_api_key)


def generate_text(settings: Settings, prompt: str) -> str:
    response = _client(settings).models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
    )
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini returned an empty response")
    return text.strip()


def generate_text_with_document(
    settings: Settings,
    prompt: str,
    *,
    content_type: str,
    content_base64: str,
) -> str:
    try:
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "google-genai is required for Gemini calls. Install requirements.txt.",
        ) from exc

    document_bytes = base64.b64decode(content_base64)
    parts: Sequence[object] = [
        prompt,
        types.Part.from_bytes(data=document_bytes, mime_type=content_type),
    ]
    response = _client(settings).models.generate_content(
        model=settings.gemini_model,
        contents=parts,
    )
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini returned an empty response")
    return text.strip()

