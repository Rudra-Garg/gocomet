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


def test_validator_accepts_allowed_lists_and_incoterm_location_suffix() -> None:
    extraction = ExtractionOutput(
        run_id="run-1",
        invoice_number=ExtractedField(value="INV-2026-104", confidence=0.95),
        consignee_name=ExtractedField(value="ABC Imports Pvt Ltd", confidence=0.99),
        hs_code=ExtractedField(value="847330, 851762", confidence=0.99),
        port_of_loading=ExtractedField(value="Shenzhen", confidence=0.97),
        port_of_discharge=ExtractedField(
            value="Nhava Sheva, Navi Mumbai",
            confidence=0.97,
        ),
        incoterms=ExtractedField(value="FOB Shenzhen", confidence=0.98),
        description_of_goods=ExtractedField(
            value="Laptop Motherboards; Wireless Communication Modules",
            confidence=0.9,
        ),
        gross_weight=ExtractedField(value="1725 KGS", confidence=0.9),
    )

    result = validate_extraction(
        extraction,
        {
            "consignee_name": "ABC Imports Pvt Ltd",
            "incoterms": ["FOB", "CIF"],
            "port_of_discharge": "Nhava Sheva",
            "hs_code": ["847330", "851762"],
        },
    )

    statuses = {item.field_name: item.status for item in result.results}
    assert statuses["consignee_name"] == "match"
    assert statuses["incoterms"] == "match"
    assert statuses["port_of_discharge"] == "match"
    assert statuses["hs_code"] == "match"
    assert result.has_mismatches is False
