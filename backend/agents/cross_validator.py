from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from backend.pipeline.state import ExtractionOutput

CROSS_DOCUMENT_FIELDS = [
    "consignee_name",
    "hs_code",
    "incoterms",
    "port_of_loading",
    "port_of_discharge",
]


class CrossFieldConflict(BaseModel):
    field_name: str
    status: Literal["consistent", "conflict"]
    values: dict[str, str]
    message: str


class CrossValidationResult(BaseModel):
    run_id: str
    results: list[CrossFieldConflict]


def cross_validate(
    run_id: str,
    extractions: list[ExtractionOutput],
    document_names: list[str] | None = None,
) -> CrossValidationResult:
    names = document_names or [f"Document {index + 1}" for index in range(len(extractions))]
    results = [
        _validate_field(field_name, extractions, names)
        for field_name in CROSS_DOCUMENT_FIELDS
    ]
    return CrossValidationResult(run_id=run_id, results=results)


def _validate_field(
    field_name: str,
    extractions: list[ExtractionOutput],
    document_names: list[str],
) -> CrossFieldConflict:
    values: dict[str, str] = {}
    normalized: dict[str, str] = {}

    for index, extraction in enumerate(extractions):
        field = getattr(extraction, field_name)
        if field.uncertain or field.value is None:
            continue
        value = str(field.value)
        normalized_value = _normalize(value)
        if not normalized_value:
            continue
        name = document_names[index] if index < len(document_names) else f"Document {index + 1}"
        values[name] = value
        normalized[name] = normalized_value

    if len(set(normalized.values())) > 1:
        return CrossFieldConflict(
            field_name=field_name,
            status="conflict",
            values=values,
            message=f"{field_name} differs across shipment documents.",
        )

    return CrossFieldConflict(
        field_name=field_name,
        status="consistent",
        values=values,
        message=f"{field_name} is consistent across shipment documents.",
    )


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())
