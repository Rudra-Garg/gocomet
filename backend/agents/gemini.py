from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from collections.abc import Callable
from typing import Any

from backend.config import Settings
from backend.observability import get_langfuse_client

LOGGER = logging.getLogger(__name__)


def _client(settings: Settings):
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "google-genai is required for Gemini calls. Run `uv sync`.",
        ) from exc
    return genai.Client(api_key=settings.gemini_api_key)


def generate_text(
    settings: Settings,
    prompt: str,
    *,
    run_id: str | None = None,
    agent: str | None = None,
) -> str:
    _enforce_token_budget(settings, [prompt])
    return _generate_text(settings, prompt, run_id=run_id, agent=agent)


def generate_text_with_document(
    settings: Settings,
    prompt: str,
    *,
    document_bytes: bytes,
    document_mime: str,
    run_id: str | None = None,
    agent: str | None = None,
) -> str:
    _enforce_token_budget(settings, [prompt, document_bytes])
    return _generate_text_with_document(
        settings,
        prompt,
        document_bytes=document_bytes,
        document_mime=document_mime,
        run_id=run_id,
        agent=agent,
    )


def _generate_text(
    settings: Settings,
    prompt: str,
    *,
    run_id: str | None,
    agent: str | None,
) -> str:
    return _with_generation_trace(
        settings,
        name="gemini_text",
        prompt=prompt,
        run_id=run_id,
        agent=agent,
        call=lambda: _client(settings).models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
        ),
    )


def _generate_text_with_document(
    settings: Settings,
    prompt: str,
    *,
    document_bytes: bytes,
    document_mime: str,
    run_id: str | None,
    agent: str | None,
) -> str:
    try:
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "google-genai is required for Gemini calls. Run `uv sync`.",
        ) from exc

    parts: Sequence[object] = [
        prompt,
        types.Part.from_bytes(data=document_bytes, mime_type=document_mime),
    ]
    return _with_generation_trace(
        settings,
        name="gemini_document",
        prompt=prompt,
        run_id=run_id,
        agent=agent,
        document={"mime_type": document_mime, "size_bytes": len(document_bytes)},
        call=lambda: _client(settings).models.generate_content(
            model=settings.gemini_model,
            contents=parts,
        ),
    )


def _with_generation_trace(
    settings: Settings,
    *,
    name: str,
    prompt: str,
    run_id: str | None,
    agent: str | None,
    call: Callable[[], Any],
    document: dict[str, Any] | None = None,
) -> str:
    client = get_langfuse_client(settings)
    generation_context = (
        client.start_as_current_observation(
            as_type="generation",
            name=name,
            model=settings.gemini_model,
            input=_generation_input(prompt, agent, document),
        )
        if client is not None
        else None
    )
    if generation_context is None:
        response = _call_with_retry(call, settings)
        return _response_text(response)

    with generation_context as generation:
        response = _call_with_retry(call, settings)
        text = _response_text(response)
        generation.update(
            output=text,
            usage_details=_usage_details(response),
            metadata=_generation_metadata(run_id, agent, document),
        )
        return text


def _call_with_retry(call: Callable[[], Any], settings: Settings) -> Any:
    last_error: Exception | None = None
    attempts = max(1, settings.max_retries)
    for attempt in range(attempts):
        try:
            return call()
        except Exception as exc:
            last_error = exc
            if not _is_retryable_error(exc) or attempt == attempts - 1:
                raise
            delay = min(2**attempt, 8)
            LOGGER.warning(
                "Gemini call failed with retryable error; retrying in %ss (%s/%s)",
                delay,
                attempt + 1,
                attempts,
            )
            time.sleep(delay)
    if last_error is not None:
        raise last_error
    raise RuntimeError("Gemini call failed without raising an exception")


def _is_retryable_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code in {429, 500, 502, 503, 504}:
        return True
    status = getattr(exc, "status", None)
    if status in {429, 500, 502, 503, 504}:
        return True
    message = str(exc).casefold()
    return any(token in message for token in ("503", "unavailable", "rate limit", "timeout"))


def _generation_input(
    prompt: str,
    agent: str | None,
    document: dict[str, Any] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"prompt": prompt}
    if agent:
        payload["agent"] = agent
    if document:
        payload["document"] = document
    return payload


def _generation_metadata(
    run_id: str | None,
    agent: str | None,
    document: dict[str, Any] | None,
) -> dict[str, str]:
    metadata = {"provider": "google-genai"}
    if run_id:
        metadata["run_id"] = run_id
    if agent:
        metadata["agent"] = agent
    if document:
        metadata["document_mime"] = str(document.get("mime_type"))
        metadata["document_size_bytes"] = str(document.get("size_bytes"))
    return metadata


def _response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini returned an empty response")
    return text.strip()


def _usage_details(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return {}
    details = {
        "input_tokens": getattr(usage, "prompt_token_count", None),
        "output_tokens": getattr(usage, "candidates_token_count", None),
        "total_tokens": getattr(usage, "total_token_count", None),
    }
    return {key: value for key, value in details.items() if isinstance(value, int)}


def _enforce_token_budget(settings: Settings, content: Sequence[str | bytes]) -> None:
    budget = settings.max_tokens_per_run
    try:
        from litellm import token_counter

        text_parts = [
            item if isinstance(item, str) else f"[binary:{len(item)} bytes]"
            for item in content
        ]
        token_count = token_counter(model=settings.gemini_model, messages=[
            {"role": "user", "content": "\n".join(text_parts)},
        ])
    except Exception:
        token_count = sum(_rough_token_count(item) for item in content)

    if token_count > budget:
        raise ValueError(
            f"LLM request token estimate {token_count} exceeds budget {budget}",
        )


def _rough_token_count(item: str | bytes) -> int:
    if isinstance(item, bytes):
        return max(1, len(item) // 4)
    return max(1, len(item) // 4)
