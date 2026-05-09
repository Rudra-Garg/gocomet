from backend.pipeline.state import (
    ExtractedField,
    ExtractionOutput,
    FieldValidationResult,
    PipelineState,
    RouterOutput,
    ValidationOutput,
)
from backend.storage.db import connect, get_run, init_db, list_runs, save_pipeline_run


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
            )
        }

    assert {
        "pipeline_runs",
        "extraction_fields",
        "validation_results",
        "router_decisions",
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
    assert list_runs(db_path)[0]["run_id"] == "run-1"
