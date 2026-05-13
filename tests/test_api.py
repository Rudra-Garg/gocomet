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


def test_inbox_route_returns_shipment_email_queue(monkeypatch, tmp_path) -> None:
    db_path = str(tmp_path / "validation.db")
    monkeypatch.setenv("DB_PATH", db_path)
    init_db(db_path)

    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO shipment_emails (
                run_id, sender, reply_to, subject, message_id, received_at
            )
            VALUES (
                'run-1', 'sender@example.com', 'reply@example.com',
                'Shipment docs', 'message-1', '2026-05-13T00:00:00+00:00'
            )
            """,
        )

    result = routes.get_inbox()

    assert result == [
        {
            "run_id": "run-1",
            "sender": "sender@example.com",
            "subject": "Shipment docs",
            "received_at": "2026-05-13T00:00:00+00:00",
            "customer_id": None,
            "action": None,
            "has_mismatches": None,
            "has_uncertain": None,
        },
    ]
