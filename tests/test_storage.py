from backend.pipeline.state import (
    ExtractedField,
    ExtractionOutput,
    FieldValidationResult,
    PipelineState,
    RouterOutput,
    ValidationOutput,
)
from backend.storage.db import connect, get_run, init_db, list_inbox, list_runs, save_pipeline_run
from backend.storage.db import (
    get_shipment_email,
    list_shipment_replies,
    save_shipment_email,
    save_shipment_reply,
)


def test_init_db_creates_required_tables_and_columns(tmp_path) -> None:
    db_path = str(tmp_path / "validation.db")
    init_db(db_path)

    with connect(db_path) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'",
            )
        }
        columns = {
            table: [
                row["name"]
                for row in connection.execute(f"PRAGMA table_info({table})")
            ]
            for table in (
                "pipeline_runs",
                "extraction_fields",
                "validation_results",
                "router_decisions",
                "cross_validation_results",
                "document_extraction_fields",
                "shipment_emails",
                "shipment_replies",
                "shipment_documents",
            )
        }

    assert {
        "pipeline_runs",
        "extraction_fields",
        "validation_results",
        "router_decisions",
        "cross_validation_results",
        "document_extraction_fields",
        "shipment_emails",
        "shipment_replies",
        "shipment_documents",
    } <= tables
    assert columns["pipeline_runs"] == [
        "run_id",
        "customer_id",
        "document_name",
        "action",
        "has_mismatches",
        "has_uncertain",
        "created_at",
    ]
    assert columns["extraction_fields"] == [
        "id",
        "run_id",
        "field_name",
        "value",
        "confidence",
        "uncertain",
    ]
    assert columns["validation_results"] == [
        "id",
        "run_id",
        "field_name",
        "status",
        "found",
        "expected",
        "rule_ref",
    ]
    assert columns["router_decisions"] == [
        "run_id",
        "action",
        "reasoning",
        "amendment_email",
        "created_at",
    ]
    assert columns["cross_validation_results"] == [
        "id",
        "run_id",
        "field_name",
        "status",
        "values_json",
        "message",
    ]
    assert columns["document_extraction_fields"] == [
        "id",
        "run_id",
        "attachment_index",
        "filename",
        "field_name",
        "value",
        "confidence",
        "uncertain",
    ]


def test_save_pipeline_run_persists_full_run(tmp_path) -> None:
    db_path = str(tmp_path / "validation.db")
    state = PipelineState(
        run_id="run-1",
        customer_id="acme",
        document_bytes=b"pdf",
        document_mime="application/pdf",
        extraction=ExtractionOutput(
            run_id="run-1",
            invoice_number=ExtractedField(value="INV-1", confidence=0.97),
            consignee_name=ExtractedField(value="ACME Corporation", confidence=0.97),
            hs_code=ExtractedField(value="8471.30", confidence=0.97),
            port_of_loading=ExtractedField(value="Shanghai, CN", confidence=0.97),
            port_of_discharge=ExtractedField(value="Los Angeles, US", confidence=0.97),
            incoterms=ExtractedField(value="FOB", confidence=0.97),
            description_of_goods=ExtractedField(value="Laptops", confidence=0.97),
            gross_weight=ExtractedField(value="100 KG", confidence=0.97),
        ),
        validation=ValidationOutput(
            run_id="run-1",
            results=[
                FieldValidationResult(
                    field_name="incoterms",
                    status="match",
                    found="FOB",
                    expected="FOB",
                    rule_ref="incoterms",
                ),
            ],
            has_mismatches=False,
            has_uncertain=False,
        ),
        decision=RouterOutput(
            run_id="run-1",
            action="auto_approve",
            reasoning="All configured rules match.",
        ),
        error=None,
    )
    state["metadata"] = {"document_name": "invoice.pdf"}  # type: ignore[typeddict-unknown-key]

    save_pipeline_run(state, db_path)

    run = get_run("run-1", db_path)
    assert run is not None
    assert run["document_name"] == "invoice.pdf"
    assert run["action"] == "auto_approve"
    assert run["extraction"][0]["field_name"] == "invoice_number"
    assert run["validation"][0]["status"] == "match"
    assert run["decision"]["reasoning"] == "All configured rules match."
    assert run["cross_validation"] == []
    assert run["document_extractions"] == []
    assert run["documents"] == []
    assert list_runs(db_path)[0]["run_id"] == "run-1"


def test_save_pipeline_run_persists_document_extractions(tmp_path) -> None:
    db_path = str(tmp_path / "validation.db")
    state = PipelineState(
        run_id="run-1",
        customer_id="acme",
        document_bytes=b"pdf",
        document_mime="application/pdf",
        extraction=ExtractionOutput(
            run_id="run-1",
            invoice_number=ExtractedField(value="INV-1", confidence=0.97),
            consignee_name=ExtractedField(value="ACME Corporation", confidence=0.97),
            hs_code=ExtractedField(value="8471.30", confidence=0.97),
            port_of_loading=ExtractedField(value="Shanghai, CN", confidence=0.97),
            port_of_discharge=ExtractedField(value="Los Angeles, US", confidence=0.97),
            incoterms=ExtractedField(value="FOB", confidence=0.97),
            description_of_goods=ExtractedField(value="Laptops", confidence=0.97),
            gross_weight=ExtractedField(value="100 KG", confidence=0.97),
        ),
        document_extractions=[
            {
                "attachment_index": 0,
                "filename": "invoice.pdf",
                "extraction": ExtractionOutput(
                    run_id="run-1",
                    invoice_number=ExtractedField(value="INV-1", confidence=0.97),
                    consignee_name=ExtractedField(value="ACME Corporation", confidence=0.97),
                    hs_code=ExtractedField(value="8471.30", confidence=0.97),
                    port_of_loading=ExtractedField(value="Shanghai, CN", confidence=0.97),
                    port_of_discharge=ExtractedField(value="Los Angeles, US", confidence=0.97),
                    incoterms=ExtractedField(value="FOB", confidence=0.97),
                    description_of_goods=ExtractedField(value="Laptops", confidence=0.97),
                    gross_weight=ExtractedField(value="100 KG", confidence=0.97),
                ),
            },
        ],
        validation=ValidationOutput(
            run_id="run-1",
            results=[],
            has_mismatches=False,
            has_uncertain=False,
        ),
        decision=None,
        error=None,
    )
    state["metadata"] = {"document_name": "invoice.pdf"}  # type: ignore[typeddict-unknown-key]

    save_pipeline_run(state, db_path)

    run = get_run("run-1", db_path)
    assert run is not None
    assert run["document_extractions"] == [
        {
            "attachment_index": 0,
            "filename": "invoice.pdf",
            "fields": [
                {
                    "field_name": "invoice_number",
                    "value": "INV-1",
                    "confidence": 0.97,
                    "uncertain": False,
                },
                {
                    "field_name": "consignee_name",
                    "value": "ACME Corporation",
                    "confidence": 0.97,
                    "uncertain": False,
                },
                {
                    "field_name": "hs_code",
                    "value": "8471.30",
                    "confidence": 0.97,
                    "uncertain": False,
                },
                {
                    "field_name": "port_of_loading",
                    "value": "Shanghai, CN",
                    "confidence": 0.97,
                    "uncertain": False,
                },
                {
                    "field_name": "port_of_discharge",
                    "value": "Los Angeles, US",
                    "confidence": 0.97,
                    "uncertain": False,
                },
                {
                    "field_name": "incoterms",
                    "value": "FOB",
                    "confidence": 0.97,
                    "uncertain": False,
                },
                {
                    "field_name": "description_of_goods",
                    "value": "Laptops",
                    "confidence": 0.97,
                    "uncertain": False,
                },
                {
                    "field_name": "gross_weight",
                    "value": "100 KG",
                    "confidence": 0.97,
                    "uncertain": False,
                },
            ],
        },
    ]


def test_email_metadata_and_reply_helpers_work(tmp_path) -> None:
    db_path = str(tmp_path / "validation.db")

    save_shipment_email(
        "run-1",
        {
            "sender": "sender@example.com",
            "reply_to": "reply@example.com",
            "subject": "Shipment docs",
            "message_id": "message-1",
            "received_at": "2026-05-13T00:00:00+00:00",
        },
        db_path,
    )
    save_shipment_reply(
        "run-1",
        sent_to="reply@example.com",
        subject="Re: Shipment docs",
        body="Please amend.",
        db_path=db_path,
    )

    email = get_shipment_email("run-1", db_path)
    replies = list_shipment_replies("run-1", db_path)

    assert email["reply_to"] == "reply@example.com"
    assert replies[0]["body"] == "Please amend."


def test_list_inbox_returns_email_queue_with_run_status(tmp_path) -> None:
    db_path = str(tmp_path / "validation.db")
    init_db(db_path)

    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO pipeline_runs (
                run_id, customer_id, document_name, action,
                has_mismatches, has_uncertain, created_at
            )
            VALUES ('run-1', 'acme', 'invoice.pdf', 'draft_amendment', 1, 0, '2026-05-13')
            """,
        )

    save_shipment_email(
        "run-1",
        {
            "sender": "sender@example.com",
            "reply_to": "reply@example.com",
            "subject": "Shipment docs",
            "message_id": "message-1",
            "received_at": "2026-05-13T12:00:00+00:00",
        },
        db_path,
    )
    save_shipment_email(
        "run-without-status",
        {
            "sender": "other@example.com",
            "reply_to": "other@example.com",
            "subject": "Queued shipment",
            "message_id": "message-2",
            "received_at": "2026-05-13T13:00:00+00:00",
        },
        db_path,
    )

    inbox = list_inbox(db_path)

    assert [item["run_id"] for item in inbox] == ["run-without-status", "run-1"]
    assert inbox[0]["action"] is None
    assert inbox[0]["has_mismatches"] is None
    assert inbox[1]["customer_id"] == "acme"
    assert inbox[1]["has_mismatches"] is True
    assert inbox[1]["has_uncertain"] is False
