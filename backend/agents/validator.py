from __future__ import annotations

from backend.pipeline.state import (
    ExtractedField,
    ExtractionOutput,
    FieldValidationResult,
    ValidationOutput,
)

EXTRACTION_FIELD_NAMES = [
    "invoice_number",
    "consignee_name",
    "hs_code",
    "port_of_loading",
    "port_of_discharge",
    "incoterms",
    "description_of_goods",
    "gross_weight",
]


def validate_extraction(
    extraction: ExtractionOutput,
    ruleset: dict[str, str],
) -> ValidationOutput:
    results = [
        _validate_field(name, getattr(extraction, name), ruleset)
        for name in EXTRACTION_FIELD_NAMES
    ]
    return ValidationOutput(
        run_id=extraction.run_id,
        results=results,
        has_mismatches=any(result.status == "mismatch" for result in results),
        has_uncertain=any(result.status == "uncertain" for result in results),
    )


def _validate_field(
    field_name: str,
    field: ExtractedField,
    ruleset: dict[str, str],
) -> FieldValidationResult:
    expected = ruleset.get(field_name)
    if field.uncertain:
        return FieldValidationResult(
            field_name=field_name,
            status="uncertain",
            found=field.value,
            expected=expected,
            rule_ref=field_name,
        )

    if field_name not in ruleset:
        return FieldValidationResult(
            field_name=field_name,
            status="match",
            found=field.value,
            expected=None,
            rule_ref=None,
        )

    if field.value is not None and _normalize(field.value) == _normalize(expected):
        status = "match"
    else:
        status = "mismatch"

    return FieldValidationResult(
        field_name=field_name,
        status=status,
        found=field.value,
        expected=expected,
        rule_ref=field_name,
    )


def _normalize(value: str | None) -> str:
    return " ".join((value or "").casefold().split())
