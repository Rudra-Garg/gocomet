import pytest

from backend.config import Settings
from backend.storage import query
from backend.storage.db import connect, init_db


def test_run_nl_query_accepts_select_and_returns_rows(monkeypatch, tmp_path) -> None:
    db_path = str(tmp_path / "validation.db")
    init_db(db_path)
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO pipeline_runs (
                run_id, customer_id, document_name, action,
                has_mismatches, has_uncertain, created_at
            )
            VALUES ('run-1', 'acme', 'invoice.pdf', 'auto_approve', 0, 0, '2026-01-01')
            """,
        )

    monkeypatch.setattr(
        query,
        "generate_text",
        lambda settings, prompt, **kwargs: "```sql\nSELECT run_id, action FROM pipeline_runs\n```",
    )

    result = query.run_nl_query(
        "show runs",
        Settings(gemini_api_key="test", db_path=db_path),
    )

    assert result["sql"] == "SELECT run_id, action FROM pipeline_runs"
    assert result["columns"] == ["run_id", "action"]
    assert result["rows"] == [["run-1", "auto_approve"]]


def test_run_nl_query_rejects_non_select(monkeypatch, tmp_path) -> None:
    db_path = str(tmp_path / "validation.db")
    monkeypatch.setattr(
        query,
        "generate_text",
        lambda settings, prompt, **kwargs: "UPDATE pipeline_runs SET action = 'x'",
    )

    with pytest.raises(ValueError, match="Only SELECT queries allowed"):
        query.run_nl_query(
            "change data",
            Settings(gemini_api_key="test", db_path=db_path),
        )


def test_run_nl_query_rejects_multiple_statements(monkeypatch, tmp_path) -> None:
    db_path = str(tmp_path / "validation.db")
    monkeypatch.setattr(
        query,
        "generate_text",
        lambda settings, prompt, **kwargs: "SELECT * FROM pipeline_runs; SELECT 1",
    )

    with pytest.raises(ValueError, match="Only one SELECT"):
        query.run_nl_query(
            "show runs",
            Settings(gemini_api_key="test", db_path=db_path),
        )
