from __future__ import annotations

from backend.agents.gemini import generate_text
from backend.config import Settings
from backend.pipeline.state import RouterAction, RouterDecision, ValidationResult


def decide_route(validation: ValidationResult, settings: Settings) -> RouterDecision:
    action = _determine_action(validation)
    prompt = f"""
You are preparing a concise trade document validation decision.

Action: {action.value}
Validation data:
{validation.model_dump_json(indent=2)}

Return a short reason. If the action is draft_amendment, also include a concise
amendment request email body after a line containing exactly EMAIL:.
""".strip()

    generated = generate_text(settings, prompt)
    reasoning, amendment_email = _split_email(generated)
    return RouterDecision(
        action=action,
        reasoning=reasoning.strip(),
        amendment_email=amendment_email.strip() if amendment_email else None,
    )


def _determine_action(validation: ValidationResult) -> RouterAction:
    if validation.uncertain_count > 0:
        return RouterAction.FLAG_REVIEW
    if validation.mismatched_count > 0:
        return RouterAction.DRAFT_AMENDMENT
    return RouterAction.AUTO_APPROVE


def _split_email(text: str) -> tuple[str, str | None]:
    marker = "EMAIL:"
    if marker not in text:
        return text, None
    reasoning, email = text.split(marker, 1)
    return reasoning, email

