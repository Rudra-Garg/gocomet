from __future__ import annotations

import json
import re

from pydantic import ValidationError

from backend.agents.gemini import generate_text_with_document
from backend.config import Settings
from backend.pipeline.state import DocumentInput, ExtractionResult


def _strip_fences(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()


def extract_document(document: DocumentInput, settings: Settings) -> ExtractionResult:
    validation_feedback = ""
    last_error: Exception | None = None

    for attempt in range(1, settings.extraction_retry_cap + 1):
        prompt = f"""
Extract trade document fields from the attached document.

Return only JSON matching this schema:
{{
  "fields": [
    {{
      "name": "consignee_name",
      "value": "string or null",
      "confidence": 0.0,
      "source_text": "short evidence or null"
    }}
  ],
  "summary": "short summary"
}}

Include at least these fields when present:
consignee_name, incoterms, port_of_discharge, hs_code.
Confidence must be between 0 and 1.
Attempt: {attempt}
{validation_feedback}
""".strip()

        try:
            response = generate_text_with_document(
                settings,
                prompt,
                content_type=document.content_type,
                content_base64=document.content_base64,
            )
            payload = json.loads(_strip_fences(response))
            return ExtractionResult.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            validation_feedback = (
                "Previous response failed validation. Fix these errors and return "
                f"only valid JSON: {exc}"
            )

    raise RuntimeError(f"Extraction failed after retries: {last_error}")

