from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from backend.pipeline.state import PipelineState

EXTRACTION_FIELD_NAMES = [
    "invoice_number",
    "consignee_name",
    "hs_code",
    "port_of_loading",
    "port_of_discharge",
    "incoterms",
    "description_of_goods",
    "gross_weight",
]


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
                customer_id TEXT,
                document_name TEXT,
                action TEXT,
                has_mismatches INTEGER,
                has_uncertain INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS extraction_fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                field_name TEXT,
                value TEXT,
                confidence REAL,
                uncertain INTEGER
            );

            CREATE TABLE IF NOT EXISTS validation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                field_name TEXT,
                status TEXT,
                found TEXT,
                expected TEXT,
                rule_ref TEXT
            );

            CREATE TABLE IF NOT EXISTS router_decisions (
                run_id TEXT PRIMARY KEY,
                action TEXT,
                reasoning TEXT,
                amendment_email TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            """,
        )


def save_pipeline_run(state: PipelineState, db_path: str) -> None:
    init_db(db_path)
    extraction = state.get("extraction")
    validation = state.get("validation")
    decision = state.get("decision")
    metadata = state.get("metadata", {})  # type: ignore[typeddict-item]

    with connect(db_path) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO pipeline_runs (
                    run_id, customer_id, document_name, action,
                    has_mismatches, has_uncertain
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    customer_id = excluded.customer_id,
                    document_name = excluded.document_name,
                    action = excluded.action,
                    has_mismatches = excluded.has_mismatches,
                    has_uncertain = excluded.has_uncertain
                """,
                (
                    state["run_id"],
                    state["customer_id"],
                    metadata.get("document_name"),
                    decision.action if decision else None,
                    int(validation.has_mismatches) if validation else None,
                    int(validation.has_uncertain) if validation else None,
                ),
            )

            connection.execute(
                "DELETE FROM extraction_fields WHERE run_id = ?",
                (state["run_id"],),
            )
            connection.execute(
                "DELETE FROM validation_results WHERE run_id = ?",
                (state["run_id"],),
            )
            connection.execute(
                "DELETE FROM router_decisions WHERE run_id = ?",
                (state["run_id"],),
            )

            if extraction:
                connection.executemany(
                    """
                    INSERT INTO extraction_fields (
                        run_id, field_name, value, confidence, uncertain
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            state["run_id"],
                            field_name,
                            getattr(extraction, field_name).value,
                            getattr(extraction, field_name).confidence,
                            int(getattr(extraction, field_name).uncertain),
                        )
                        for field_name in EXTRACTION_FIELD_NAMES
                    ],
                )

            if validation:
                connection.executemany(
                    """
                    INSERT INTO validation_results (
                        run_id, field_name, status, found, expected, rule_ref
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            state["run_id"],
                            item.field_name,
                            item.status,
                            item.found,
                            item.expected,
                            item.rule_ref,
                        )
                        for item in validation.results
                    ],
                )

            if decision:
                connection.execute(
                    """
                    INSERT INTO router_decisions (
                        run_id, action, reasoning, amendment_email
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        state["run_id"],
                        decision.action,
                        decision.reasoning,
                        decision.amendment_email,
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

        extraction = _fetch_all(
            connection,
            """
            SELECT field_name, value, confidence, uncertain
            FROM extraction_fields
            WHERE run_id = ?
            ORDER BY id
            """,
            (run_id,),
        )
        validation = _fetch_all(
            connection,
            """
            SELECT field_name, status, found, expected, rule_ref
            FROM validation_results
            WHERE run_id = ?
            ORDER BY id
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
        "document_name": run["document_name"],
        "action": run["action"],
        "has_mismatches": bool(run["has_mismatches"])
        if run["has_mismatches"] is not None
        else None,
        "has_uncertain": bool(run["has_uncertain"])
        if run["has_uncertain"] is not None
        else None,
        "created_at": run["created_at"],
        "error": None,
        "extraction": [_row_with_bool(row, "uncertain") for row in extraction],
        "validation": validation,
        "decision": dict(decision) if decision else None,
    }


def list_runs(db_path: str, limit: int = 20) -> list[dict]:
    init_db(db_path)
    with connect(db_path) as connection:
        rows = _fetch_all(
            connection,
            """
            SELECT run_id, customer_id, document_name, action,
                   has_mismatches, has_uncertain, created_at
            FROM pipeline_runs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
    return [
        {
            **row,
            "has_mismatches": bool(row["has_mismatches"])
            if row["has_mismatches"] is not None
            else None,
            "has_uncertain": bool(row["has_uncertain"])
            if row["has_uncertain"] is not None
            else None,
        }
        for row in rows
    ]


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


def _row_with_bool(row: dict, key: str) -> dict:
    return {**row, key: bool(row[key])}
