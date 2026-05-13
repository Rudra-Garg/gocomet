from __future__ import annotations

import json
import re

from pydantic import ValidationError

from backend.agents.gemini import generate_text_with_document
from backend.config import Settings
from backend.pipeline.state import ExtractionOutput

EXTRACTION_SYSTEM_PROMPT = (
    "You are a trade document extraction agent. Extract only what you can "
    "physically see in the document. For each field, return a value and a "
    "confidence score from 0.0 to 1.0, plus a source_snippet that is an "
    "exact document snippet of at most 120 characters supporting the value. "
    "If a field is not present or illegible, return null for value and "
    "source_snippet, and 0.0 for confidence. "
    "Never guess or infer. Return ONLY valid JSON matching the schema."
)


def extract_document(
    *,
    run_id: str,
    document_bytes: bytes,
    document_mime: str,
    settings: Settings,
) -> ExtractionOutput:
    retry_feedback = ""
    last_error: Exception | None = None

    for _ in range(3):
        prompt = _build_prompt(run_id, retry_feedback)
        try:
            response = generate_text_with_document(
                settings,
                prompt,
                document_bytes=document_bytes,
                document_mime=document_mime,
                run_id=run_id,
                agent="extractor",
            )
            payload = json.loads(_strip_fences(response))
            return ExtractionOutput.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            retry_feedback = (
                f"Previous output failed with: {exc}. Return corrected JSON."
            )

    raise RuntimeError(f"Extraction failed after retries: {last_error}")


def _build_prompt(run_id: str, retry_feedback: str) -> str:
    prompt = f"""
{EXTRACTION_SYSTEM_PROMPT}

Return JSON with this exact top-level shape:
{{
  "run_id": "{run_id}",
  "invoice_number": {{"value": "string or null", "confidence": 0.0, "source_snippet": "exact source text or null"}},
  "consignee_name": {{"value": "string or null", "confidence": 0.0, "source_snippet": "exact source text or null"}},
  "hs_code": {{"value": "string or null", "confidence": 0.0, "source_snippet": "exact source text or null"}},
  "port_of_loading": {{"value": "string or null", "confidence": 0.0, "source_snippet": "exact source text or null"}},
  "port_of_discharge": {{"value": "string or null", "confidence": 0.0, "source_snippet": "exact source text or null"}},
  "incoterms": {{"value": "string or null", "confidence": 0.0, "source_snippet": "exact source text or null"}},
  "description_of_goods": {{"value": "string or null", "confidence": 0.0, "source_snippet": "exact source text or null"}},
  "gross_weight": {{"value": "string or null", "confidence": 0.0, "source_snippet": "exact source text or null"}}
}}

Every source_snippet must be copied exactly from the document, must be 120 characters or fewer, and must be null when value is null.
For hs_code, include every visible HS/HTS code as a comma-separated string.
For incoterms, return only the standard code, such as FOB or CIF, not the place.
""".strip()
    if retry_feedback:
        prompt = f"{prompt}\n\n{retry_feedback}"
    return prompt


def _strip_fences(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()
