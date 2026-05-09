from backend.agents.validator import validate_extraction
from backend.pipeline.state import ExtractedField, ExtractionOutput


def test_extracted_field_marks_uncertain_below_half() -> None:
    field = ExtractedField(value="CIF", confidence=0.49)

    assert field.uncertain is True


def test_validator_marks_match_mismatch_uncertain_and_no_rule_as_match() -> None:
    extraction = ExtractionOutput(
        run_id="run-1",
        invoice_number=ExtractedField(value="INV-1", confidence=0.95),
        consignee_name=ExtractedField(value=" acme corporation ", confidence=0.99),
        hs_code=ExtractedField(value="8471.30", confidence=0.99),
        port_of_loading=ExtractedField(value="Shanghai, CN", confidence=0.97),
        port_of_discharge=ExtractedField(value=None, confidence=0.2),
        incoterms=ExtractedField(value="CIF", confidence=0.98),
        description_of_goods=ExtractedField(value="Laptops", confidence=0.9),
        gross_weight=ExtractedField(value="100 KG", confidence=0.9),
    )

    result = validate_extraction(
        extraction,
        {
            "consignee_name": "ACME Corporation",
            "incoterms": "FOB",
            "port_of_discharge": "Los Angeles, US",
        },
    )

    statuses = {item.field_name: item.status for item in result.results}
    assert statuses["consignee_name"] == "match"
    assert statuses["incoterms"] == "mismatch"
    assert statuses["port_of_discharge"] == "uncertain"
    assert statuses["invoice_number"] == "match"
    assert result.has_mismatches is True
    assert result.has_uncertain is True
