from backend.pipeline.state import (
    ExtractionResult,
    ExtractedField,
    PipelineState,
    RouterAction,
    RouterDecision,
    ValidationItem,
    ValidationResult,
)
from backend.storage.db import connect, get_run, init_db, list_runs, save_pipeline_run


def test_init_db_creates_required_tables(tmp_path) -> None:
    db_path = str(tmp_path / "validation.db")
    init_db(db_path)

    with connect(db_path) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'",
            )
        }

    assert {
        "pipeline_runs",
        "extracted_fields",
        "validation_results",
        "router_decisions",
    } <= tables


def test_save_pipeline_run_persists_full_run(tmp_path) -> None:
    db_path = str(tmp_path / "validation.db")
    state = PipelineState(
        run_id="run-1",
        customer_id="acme",
        extraction=ExtractionResult(
            fields=[
                ExtractedField(
                    name="incoterms",
                    value="FOB",
                    confidence=0.97,
                    source_text="FOB",
                ),
            ],
        ),
        validation=ValidationResult(
            items=[
                ValidationItem(
                    field="incoterms",
                    expected="FOB",
                    actual="FOB",
                    status="match",
                    confidence=0.97,
                    message="Extracted value matches the customer rule.",
                ),
            ],
            matched_count=1,
        ),
        decision=RouterDecision(
            action=RouterAction.AUTO_APPROVE,
            reasoning="All configured rules match.",
        ),
    )

    save_pipeline_run(state, db_path)

    run = get_run("run-1", db_path)
    assert run is not None
    assert run["action"] == "auto_approve"
    assert run["extraction"]["fields"][0]["name"] == "incoterms"
    assert run["validation"]["items"][0]["status"] == "match"
    assert run["decision"]["reasoning"] == "All configured rules match."
    assert list_runs(db_path)[0]["run_id"] == "run-1"
