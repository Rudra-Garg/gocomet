from backend.agents.router import _determine_action
from backend.pipeline.state import RouterAction, ValidationItem, ValidationResult


def test_router_flags_any_uncertain_first() -> None:
    validation = ValidationResult(
        items=[
            ValidationItem(
                field="incoterms",
                expected="FOB",
                actual="CIF",
                status="mismatch",
                confidence=0.95,
                message="Mismatch",
            ),
            ValidationItem(
                field="hs_code",
                expected="8471.30",
                actual=None,
                status="uncertain",
                confidence=0,
                message="Missing",
            ),
        ],
        mismatched_count=1,
        uncertain_count=1,
    )

    assert _determine_action(validation) == RouterAction.FLAG_REVIEW


def test_router_drafts_amendment_for_mismatch_without_uncertainty() -> None:
    validation = ValidationResult(
        items=[
            ValidationItem(
                field="incoterms",
                expected="FOB",
                actual="CIF",
                status="mismatch",
                confidence=0.95,
                message="Mismatch",
            ),
        ],
        mismatched_count=1,
    )

    assert _determine_action(validation) == RouterAction.DRAFT_AMENDMENT


def test_router_auto_approves_clean_validation() -> None:
    validation = ValidationResult(
        items=[
            ValidationItem(
                field="incoterms",
                expected="FOB",
                actual="FOB",
                status="match",
                confidence=0.95,
                message="Match",
            ),
        ],
        matched_count=1,
    )

    assert _determine_action(validation) == RouterAction.AUTO_APPROVE

