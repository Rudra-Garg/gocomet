from backend.agents.cross_validator import cross_validate
from backend.pipeline.state import ExtractedField, ExtractionOutput


def test_conflicting_hs_codes_between_documents_returns_conflict() -> None:
    result = cross_validate(
        "run-1",
        [
            _extraction(hs_code="8471.30"),
            _extraction(hs_code="9503.00"),
        ],
        ["invoice.pdf", "packing.pdf"],
    )

    hs_code = next(item for item in result.results if item.field_name == "hs_code")
    assert hs_code.status == "conflict"
    assert hs_code.values == {
        "invoice.pdf": "8471.30",
        "packing.pdf": "9503.00",
    }


def test_consignee_whitespace_only_difference_returns_consistent() -> None:
    result = cross_validate(
        "run-1",
        [
            _extraction(consignee_name="ACME   Corporation"),
            _extraction(consignee_name=" acme corporation "),
        ],
        ["invoice.pdf", "packing.pdf"],
    )

    consignee = next(item for item in result.results if item.field_name == "consignee_name")
    assert consignee.status == "consistent"


def _extraction(
    *,
    consignee_name: str = "ACME Corporation",
    hs_code: str = "8471.30",
) -> ExtractionOutput:
    return ExtractionOutput(
        run_id="run-1",
        invoice_number=ExtractedField(value="INV-1", confidence=0.97),
        consignee_name=ExtractedField(value=consignee_name, confidence=0.97),
        hs_code=ExtractedField(value=hs_code, confidence=0.97),
        port_of_loading=ExtractedField(value="Shanghai", confidence=0.97),
        port_of_discharge=ExtractedField(value="Los Angeles", confidence=0.97),
        incoterms=ExtractedField(value="FOB", confidence=0.97),
        description_of_goods=ExtractedField(value="Laptops", confidence=0.97),
        gross_weight=ExtractedField(value="100 KG", confidence=0.97),
    )
