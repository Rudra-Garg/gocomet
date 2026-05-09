from __future__ import annotations

import os
import logging
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from typing import Any

from backend.config import Settings

logger = logging.getLogger(__name__)

_CLIENT = None
_CLIENT_CONFIG: tuple[str, str, str] | None = None


def langfuse_enabled(settings: Settings) -> bool:
    return bool(settings.langfuse_public_key and settings.langfuse_secret_key)


def get_langfuse_client(settings: Settings):
    global _CLIENT, _CLIENT_CONFIG

    if not langfuse_enabled(settings):
        return None

    base_url = settings.langfuse_base_url.rstrip("/")
    client_config = (
        settings.langfuse_public_key or "",
        settings.langfuse_secret_key or "",
        base_url,
    )
    if _CLIENT is not None and _CLIENT_CONFIG == client_config:
        return _CLIENT
    if _CLIENT is not None:
        try:
            _CLIENT.shutdown()
        except Exception:
            logger.warning("Failed to shut down previous Langfuse client", exc_info=True)
        _CLIENT = None

    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key or ""
    os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key or ""
    os.environ["LANGFUSE_BASE_URL"] = base_url
    os.environ["LANGFUSE_HOST"] = base_url
    try:
        from langfuse import Langfuse

        _CLIENT = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            base_url=base_url,
        )
        _CLIENT_CONFIG = client_config
        return _CLIENT
    except Exception:
        logger.warning("Failed to initialize Langfuse client", exc_info=True)
        _CLIENT_CONFIG = None
        return None


def flush_langfuse(settings: Settings) -> None:
    client = get_langfuse_client(settings)
    if client is None:
        return
    try:
        client.flush()
    except Exception:
        logger.warning("Failed to flush Langfuse traces", exc_info=True)
        return


@contextmanager
def trace_span(
    settings: Settings,
    *,
    name: str,
    input: dict[str, Any] | None = None,
    output: dict[str, Any] | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    as_type: str = "span",
) -> Iterator[Any | None]:
    client = get_langfuse_client(settings)
    if client is None:
        yield None
        return

    attributes = _attributes_context(
        trace_name=name,
        session_id=session_id,
        metadata=metadata,
        tags=tags,
    )
    with client.start_as_current_observation(
        as_type=as_type,
        name=name,
        input=input,
    ) as observation:
        with attributes:
            yield observation
        if output is not None:
            observation.update(output=output)


def _attributes_context(
    *,
    trace_name: str,
    session_id: str | None,
    metadata: dict[str, Any] | None,
    tags: list[str] | None,
):
    try:
        from langfuse import propagate_attributes
    except Exception:
        return nullcontext()

    return propagate_attributes(
        trace_name=trace_name,
        session_id=session_id,
        metadata=_string_metadata(metadata or {}),
        tags=tags or [],
    )


def _string_metadata(metadata: dict[str, Any]) -> dict[str, str]:
    return {
        str(key): str(value)[:200]
        for key, value in metadata.items()
        if value is not None
    }
