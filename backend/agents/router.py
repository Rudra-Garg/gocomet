from __future__ import annotations

from backend.agents.gemini import generate_text
from backend.config import Settings
from backend.pipeline.state import FieldValidationResult, RouterOutput, ValidationOutput


def decide_route(validation: ValidationOutput, settings: Settings) -> RouterOutput:
    action = _determine_action(validation)
    reasoning = generate_text(
        settings,
        _reasoning_prompt(validation, action),
        run_id=validation.run_id,
        agent="router",
    )
    amendment_email = None
    if action == "draft_amendment":
        amendment_email = generate_text(
            settings,
            _amendment_prompt(_mismatches(validation)),
            run_id=validation.run_id,
            agent="router",
        )

    return RouterOutput(
        run_id=validation.run_id,
        action=action,
        reasoning=reasoning.strip(),
        amendment_email=amendment_email.strip() if amendment_email else None,
    )


def _determine_action(validation: ValidationOutput) -> str:
    if validation.has_uncertain:
        return "flag_review"
    if validation.has_mismatches:
        return "draft_amendment"
    return "auto_approve"


def _reasoning_prompt(validation: ValidationOutput, action: str) -> str:
    uncertain = [
        result.model_dump()
        for result in validation.results
        if result.status == "uncertain"
    ]
    mismatches = [
        result.model_dump()
        for result in validation.results
        if result.status == "mismatch"
    ]
    matches = [
        result.field_name
        for result in validation.results
        if result.status == "match"
    ]
    return f"""
Write 2-3 sentences explaining this trade document routing decision to a logistics operator in plain English.

Action: {action}
Matched fields: {matches}
Uncertain fields: {uncertain}
Mismatched fields: {mismatches}
""".strip()


def _amendment_prompt(mismatches: list[FieldValidationResult]) -> str:
    mismatch_lines = "\n".join(
        f"Field: {item.field_name} | Found: {item.found} | Expected: {item.expected}"
        for item in mismatches
    )
    return f"""
Write a professional amendment request email to a supplier.
 List each discrepancy as: Field: {{field_name}} | Found: {{found}} | Expected: {{expected}}
 Be specific and concise. Do not add pleasantries beyond a single opening line.
 Sign off as 'Cargo Group Validation Team'.

Discrepancies:
{mismatch_lines}
""".strip()


def _mismatches(validation: ValidationOutput) -> list[FieldValidationResult]:
    return [result for result in validation.results if result.status == "mismatch"]
