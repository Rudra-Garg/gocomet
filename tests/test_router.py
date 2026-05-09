from backend.agents import router
from backend.pipeline.state import FieldValidationResult, ValidationOutput


def test_router_flags_any_uncertain_first() -> None:
    validation = ValidationOutput(
        run_id="run-1",
        results=[
            FieldValidationResult(
                field_name="incoterms",
                status="mismatch",
                found="CIF",
                expected="FOB",
            ),
            FieldValidationResult(
                field_name="hs_code",
                status="uncertain",
                found=None,
                expected="8471.30",
            ),
        ],
        has_mismatches=True,
        has_uncertain=True,
    )

    assert router._determine_action(validation) == "flag_review"


def test_router_drafts_amendment_for_mismatch_without_uncertainty() -> None:
    validation = ValidationOutput(
        run_id="run-1",
        results=[
            FieldValidationResult(
                field_name="incoterms",
                status="mismatch",
                found="CIF",
                expected="FOB",
            ),
        ],
        has_mismatches=True,
        has_uncertain=False,
    )

    assert router._determine_action(validation) == "draft_amendment"


def test_router_auto_approves_clean_validation() -> None:
    validation = ValidationOutput(
        run_id="run-1",
        results=[
            FieldValidationResult(
                field_name="incoterms",
                status="match",
                found="FOB",
                expected="FOB",
            ),
        ],
        has_mismatches=False,
        has_uncertain=False,
    )

    assert router._determine_action(validation) == "auto_approve"


def test_router_amendment_prompt_includes_every_mismatch() -> None:
    prompt = router._amendment_prompt(
        [
            FieldValidationResult(
                field_name="incoterms",
                status="mismatch",
                found="CIF",
                expected="FOB",
            ),
            FieldValidationResult(
                field_name="hs_code",
                status="mismatch",
                found="1234",
                expected="8471.30",
            ),
        ],
    )

    assert "Field: incoterms | Found: CIF | Expected: FOB" in prompt
    assert "Field: hs_code | Found: 1234 | Expected: 8471.30" in prompt
    assert "Cargo Group Validation Team" in prompt
