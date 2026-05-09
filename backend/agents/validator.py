from __future__ import annotations

from backend.pipeline.state import (
    ExtractionResult,
    ValidationItem,
    ValidationResult,
    ValidationStatus,
)


def validate_extraction(
    extraction: ExtractionResult,
    ruleset: dict[str, str],
    confidence_threshold: float,
) -> ValidationResult:
    fields = {field.name: field for field in extraction.fields}
    items: list[ValidationItem] = []

    for name, field in fields.items():
        expected = ruleset.get(name)
        actual = field.value
        if expected is None:
            status = ValidationStatus.NO_RULE
            message = "No customer rule is configured for this field."
        elif field.confidence < confidence_threshold or actual is None:
            status = ValidationStatus.UNCERTAIN
            message = "Extracted value is below the confidence threshold."
        elif _normalize(actual) == _normalize(expected):
            status = ValidationStatus.MATCH
            message = "Extracted value matches the customer rule."
        else:
            status = ValidationStatus.MISMATCH
            message = "Extracted value differs from the customer rule."

        items.append(
            ValidationItem(
                field=name,
                expected=expected,
                actual=actual,
                status=status,
                confidence=field.confidence,
                message=message,
            ),
        )

    for name, expected in ruleset.items():
        if name not in fields:
            items.append(
                ValidationItem(
                    field=name,
                    expected=expected,
                    actual=None,
                    status=ValidationStatus.UNCERTAIN,
                    confidence=0,
                    message="Required field was not extracted.",
                ),
            )

    return ValidationResult(
        items=items,
        matched_count=sum(item.status == ValidationStatus.MATCH for item in items),
        mismatched_count=sum(item.status == ValidationStatus.MISMATCH for item in items),
        uncertain_count=sum(item.status == ValidationStatus.UNCERTAIN for item in items),
        no_rule_count=sum(item.status == ValidationStatus.NO_RULE for item in items),
    )


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())

