from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from backend.pipeline.state import PipelineState


def connect(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path: str) -> None:
    with connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                action TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS extracted_fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                name TEXT NOT NULL,
                value TEXT,
                confidence REAL NOT NULL,
                source_text TEXT,
                FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
            );

            CREATE TABLE IF NOT EXISTS validation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                field TEXT NOT NULL,
                expected TEXT,
                actual TEXT,
                status TEXT NOT NULL,
                confidence REAL NOT NULL,
                message TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
            );

            CREATE TABLE IF NOT EXISTS router_decisions (
                run_id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                reasoning TEXT NOT NULL,
                amendment_email TEXT,
                FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
            );
            """,
        )


def save_pipeline_run(state: PipelineState, db_path: str) -> None:
    init_db(db_path)
    with connect(db_path) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO pipeline_runs (
                    run_id, customer_id, action, error, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    customer_id = excluded.customer_id,
                    action = excluded.action,
                    error = excluded.error,
                    updated_at = excluded.updated_at
                """,
                (
                    state.run_id,
                    state.customer_id,
                    state.decision.action.value if state.decision else None,
                    state.error,
                    state.created_at.isoformat(),
                    datetime.now(UTC).isoformat(),
                ),
            )

            connection.execute("DELETE FROM extracted_fields WHERE run_id = ?", (state.run_id,))
            connection.execute(
                "DELETE FROM validation_results WHERE run_id = ?",
                (state.run_id,),
            )
            connection.execute("DELETE FROM router_decisions WHERE run_id = ?", (state.run_id,))

            if state.extraction:
                connection.executemany(
                    """
                    INSERT INTO extracted_fields (
                        run_id, name, value, confidence, source_text
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            state.run_id,
                            field.name,
                            field.value,
                            field.confidence,
                            field.source_text,
                        )
                        for field in state.extraction.fields
                    ],
                )

            if state.validation:
                connection.executemany(
                    """
                    INSERT INTO validation_results (
                        run_id, field, expected, actual, status, confidence, message
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            state.run_id,
                            item.field,
                            item.expected,
                            item.actual,
                            item.status.value,
                            item.confidence,
                            item.message,
                        )
                        for item in state.validation.items
                    ],
                )

            if state.decision:
                connection.execute(
                    """
                    INSERT INTO router_decisions (
                        run_id, action, reasoning, amendment_email
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        state.run_id,
                        state.decision.action.value,
                        state.decision.reasoning,
                        state.decision.amendment_email,
                    ),
                )


def get_run(run_id: str, db_path: str) -> dict | None:
    init_db(db_path)
    with connect(db_path) as connection:
        run = connection.execute(
            "SELECT * FROM pipeline_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if run is None:
            return None

        extracted = _fetch_all(
            connection,
            "SELECT name, value, confidence, source_text FROM extracted_fields WHERE run_id = ?",
            (run_id,),
        )
        validation = _fetch_all(
            connection,
            """
            SELECT field, expected, actual, status, confidence, message
            FROM validation_results
            WHERE run_id = ?
            """,
            (run_id,),
        )
        decision = connection.execute(
            """
            SELECT action, reasoning, amendment_email
            FROM router_decisions
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

    return {
        "run_id": run["run_id"],
        "customer_id": run["customer_id"],
        "action": run["action"],
        "error": run["error"],
        "created_at": run["created_at"],
        "updated_at": run["updated_at"],
        "extraction": {"fields": extracted},
        "validation": {"items": validation},
        "decision": dict(decision) if decision else None,
    }


def list_runs(db_path: str) -> list[dict]:
    init_db(db_path)
    with connect(db_path) as connection:
        return _fetch_all(
            connection,
            """
            SELECT run_id, customer_id, action, error, created_at, updated_at
            FROM pipeline_runs
            ORDER BY created_at DESC
            LIMIT 100
            """,
            (),
        )


def export_rows(rows: Iterable[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]


def load_ruleset(customer_id: str) -> dict[str, str]:
    ruleset_path = Path("data") / "rulesets" / f"customer_{customer_id}.json"
    if not ruleset_path.exists():
        raise FileNotFoundError(f"No ruleset configured for customer_id={customer_id}")
    return json.loads(ruleset_path.read_text(encoding="utf-8"))


def _fetch_all(
    connection: sqlite3.Connection,
    sql: str,
    params: tuple,
) -> list[dict]:
    return [dict(row) for row in connection.execute(sql, params).fetchall()]
