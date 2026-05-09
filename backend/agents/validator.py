from __future__ import annotations

from typing import TypeAlias

from backend.pipeline.state import (
    ExtractedField,
    ExtractionOutput,
    FieldValidationResult,
    ValidationOutput,
)

RuleValue: TypeAlias = str | list[str]

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
    ruleset: dict[str, RuleValue],
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
    ruleset: dict[str, RuleValue],
) -> FieldValidationResult:
    expected = ruleset.get(field_name)
    if field.uncertain:
        return FieldValidationResult(
            field_name=field_name,
            status="uncertain",
            found=field.value,
            expected=_format_expected(expected),
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

    if field.value is not None and _matches_rule(field_name, field.value, expected):
        status = "match"
    else:
        status = "mismatch"

    return FieldValidationResult(
        field_name=field_name,
        status=status,
        found=field.value,
        expected=_format_expected(expected),
        rule_ref=field_name,
    )


def _normalize(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def _matches_rule(field_name: str, found: str, expected: RuleValue | None) -> bool:
    if expected is None:
        return False

    if isinstance(expected, list):
        allowed = {_normalize(item) for item in expected}
        found_values = _split_multi_value(found)
        if field_name == "incoterms":
            found_values = [_normalize(found).split()[0]] if found.strip() else []
        return bool(found_values) and all(value in allowed for value in found_values)

    if field_name in {"port_of_discharge", "port_of_loading"}:
        return _normalize(expected) in _normalize(found)

    return _normalize(found) == _normalize(expected)


def _split_multi_value(value: str) -> list[str]:
    return [
        _normalize(part)
        for part in value.replace("/", ",").replace(";", ",").split(",")
        if part.strip()
    ]


def _format_expected(expected: RuleValue | None) -> str | None:
    if expected is None:
        return None
    if isinstance(expected, list):
        return ", ".join(expected)
    return expected
