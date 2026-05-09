from __future__ import annotations

from collections.abc import Sequence
from functools import wraps
from typing import Any, Callable, TypeVar

from backend.config import Settings

F = TypeVar("F", bound=Callable[..., Any])


def _client(settings: Settings):
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "google-genai is required for Gemini calls. Run `uv sync`.",
        ) from exc
    return genai.Client(api_key=settings.gemini_api_key)


def observe_llm_call(name: str) -> Callable[[F], F]:
    try:
        from langfuse import observe
    except ImportError:
        observe = None

    def decorator(func: F) -> F:
        observed = observe(name=name)(func) if observe else func

        @wraps(func)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            _tag_observation(kwargs.get("run_id"), kwargs.get("agent"))
            return observed(*args, **kwargs)

        return wrapped  # type: ignore[return-value]

    return decorator


def _tag_observation(run_id: str | None, agent: str | None) -> None:
    if not run_id or not agent:
        return
    try:
        from langfuse import get_client

        get_client().update_current_trace(
            session_id=run_id,
            tags=[f"run_id:{run_id}", f"agent:{agent}"],
            metadata={"run_id": run_id, "agent": agent},
        )
    except Exception:
        return


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


@observe_llm_call("gemini_text")
def _generate_text(
    settings: Settings,
    prompt: str,
    *,
    run_id: str | None,
    agent: str | None,
) -> str:
    response = _client(settings).models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
    )
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini returned an empty response")
    return text.strip()


@observe_llm_call("gemini_document")
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
    response = _client(settings).models.generate_content(
        model=settings.gemini_model,
        contents=parts,
    )
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini returned an empty response")
    return text.strip()


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
