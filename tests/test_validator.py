from backend.agents.validator import validate_extraction
from backend.pipeline.state import ExtractedField, ExtractionResult


def test_validator_marks_match_mismatch_uncertain_and_no_rule() -> None:
    extraction = ExtractionResult(
        fields=[
            ExtractedField(
                name="consignee_name",
                value="ACME Corporation",
                confidence=0.99,
            ),
            ExtractedField(name="incoterms", value="CIF", confidence=0.98),
            ExtractedField(name="port_of_discharge", value=None, confidence=0.2),
            ExtractedField(name="invoice_number", value="INV-1", confidence=0.95),
        ],
    )

    result = validate_extraction(
        extraction,
        {
            "consignee_name": "ACME Corporation",
            "incoterms": "FOB",
            "port_of_discharge": "Los Angeles, US",
        },
        confidence_threshold=0.75,
    )

    statuses = {item.field: item.status.value for item in result.items}
    assert statuses == {
        "consignee_name": "match",
        "incoterms": "mismatch",
        "port_of_discharge": "uncertain",
        "invoice_number": "no_rule",
    }
    assert result.matched_count == 1
    assert result.mismatched_count == 1
    assert result.uncertain_count == 1
    assert result.no_rule_count == 1


def test_validator_marks_missing_rule_field_uncertain() -> None:
    result = validate_extraction(
        ExtractionResult(fields=[]),
        {"hs_code": "8471.30"},
        confidence_threshold=0.75,
    )

    assert len(result.items) == 1
    assert result.items[0].field == "hs_code"
    assert result.items[0].status.value == "uncertain"

