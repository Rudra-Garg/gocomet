from backend.api import routes
from backend.storage.db import connect, init_db


def test_runs_route_returns_json_and_limits_to_20(monkeypatch, tmp_path) -> None:
    db_path = str(tmp_path / "validation.db")
    monkeypatch.setenv("DB_PATH", db_path)
    init_db(db_path)

    with connect(db_path) as connection:
        for index in range(25):
            connection.execute(
                """
                INSERT INTO pipeline_runs (
                    run_id, customer_id, document_name, action,
                    has_mismatches, has_uncertain, created_at
                )
                VALUES (?, 'acme', 'invoice.pdf', 'auto_approve', 0, 0, ?)
                """,
                (f"run-{index}", f"2026-01-{index + 1:02d}"),
            )

    result = routes.runs()

    assert isinstance(result, list)
    assert len(result) == 20
    assert result[0]["run_id"] == "run-24"
