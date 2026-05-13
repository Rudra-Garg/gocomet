from datetime import datetime, timezone

from backend.pipeline import multi
from backend.pipeline.state import ExtractedField, ExtractionOutput, RouterOutput
from backend.trigger.models import ShipmentAttachment, ShipmentIngest


def test_synthetic_cross_doc_mismatch_rows_use_rule_ref(monkeypatch, tmp_path) -> None:
    db_path = str(tmp_path / "validation.db")

    extractions = [
        _extraction(hs_code="8471.30"),
        _extraction(hs_code="9503.00"),
    ]

    def fake_extract_document(**kwargs):
        return extractions.pop(0)

    def fake_decide_route(validation, settings):
        assert validation.has_mismatches is True
        assert any(item.rule_ref == "cross_doc_conflict" for item in validation.results)
        return RouterOutput(
            run_id=validation.run_id,
            action="draft_amendment",
            reasoning="Cross-document mismatch.",
            amendment_email="Please amend the shipment documents.",
        )

    monkeypatch.setattr(multi, "extract_document", fake_extract_document)
    monkeypatch.setattr(multi, "decide_route", fake_decide_route)

    settings = _settings(db_path)
    ingest = ShipmentIngest(
        run_id="run-1",
        customer_id="acme",
        sender="sender@example.com",
        reply_to="reply@example.com",
        subject="Shipment docs",
        message_id="message-1",
        received_at=datetime.now(timezone.utc),
        attachments=[
            ShipmentAttachment("invoice.pdf", "application/pdf", b"invoice"),
            ShipmentAttachment("packing.pdf", "application/pdf", b"packing"),
        ],
    )

    state = multi.ingest_shipment(ingest, settings)

    synthetic = [
        item for item in state["validation"].results if item.rule_ref == "cross_doc_conflict"
    ]
    assert synthetic
    assert synthetic[0].field_name == "hs_code"
    assert len(state["document_extractions"]) == 2


def test_ingest_validates_merged_extraction_with_non_null_priority(monkeypatch, tmp_path) -> None:
    db_path = str(tmp_path / "validation.db")

    extractions = [
        _extraction(
            hs_code="8471.30",
            invoice_number=None,
            invoice_confidence=0.99,
            run_id="run-2",
        ),
        _extraction(
            hs_code="8471.30",
            invoice_number="INV-2",
            invoice_confidence=0.60,
            run_id="run-2",
        ),
    ]
    original_validate_extraction = multi.validate_extraction

    def fake_extract_document(**kwargs):
        return extractions.pop(0)

    def fake_validate_extraction(extraction, ruleset):
        assert extraction.invoice_number.value == "INV-2"
        assert extraction.invoice_number.confidence == 0.60
        return original_validate_extraction(extraction, ruleset)

    def fake_decide_route(validation, settings):
        return RouterOutput(
            run_id=validation.run_id,
            action="auto_approve",
            reasoning="Merged extraction validated.",
        )

    monkeypatch.setattr(multi, "extract_document", fake_extract_document)
    monkeypatch.setattr(multi, "validate_extraction", fake_validate_extraction)
    monkeypatch.setattr(multi, "decide_route", fake_decide_route)

    settings = _settings(db_path)
    ingest = ShipmentIngest(
        run_id="run-2",
        customer_id="acme",
        sender="sender@example.com",
        reply_to="reply@example.com",
        subject="Shipment docs",
        message_id="message-2",
        received_at=datetime.now(timezone.utc),
        attachments=[
            ShipmentAttachment("packing.pdf", "application/pdf", b"packing"),
            ShipmentAttachment("invoice.pdf", "application/pdf", b"invoice"),
        ],
    )

    state = multi.ingest_shipment(ingest, settings)

    assert state["extraction"].invoice_number.value == "INV-2"


def _extraction(
    hs_code: str,
    invoice_number: str | None = "INV-1",
    invoice_confidence: float = 0.97,
    run_id: str = "run-1",
) -> ExtractionOutput:
    return ExtractionOutput(
        run_id=run_id,
        invoice_number=ExtractedField(value=invoice_number, confidence=invoice_confidence),
        consignee_name=ExtractedField(value="ACME Corporation", confidence=0.97),
        hs_code=ExtractedField(value=hs_code, confidence=0.97),
        port_of_loading=ExtractedField(value="Shanghai", confidence=0.97),
        port_of_discharge=ExtractedField(value="Los Angeles", confidence=0.97),
        incoterms=ExtractedField(value="FOB", confidence=0.97),
        description_of_goods=ExtractedField(value="Laptops", confidence=0.97),
        gross_weight=ExtractedField(value="100 KG", confidence=0.97),
    )


def _settings(db_path: str):
    from backend.config import Settings

    return Settings(
        gemini_api_key="test-key",
        db_path=db_path,
        checkpoint_db_path=f"{db_path}.checkpoint",
    )
