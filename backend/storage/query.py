from __future__ import annotations

import re

from backend.agents.gemini import generate_text
from backend.config import Settings
from backend.observability import trace_span
from backend.storage.db import connect, init_db

SCHEMA_PROMPT = """
SQLite schema:

pipeline_runs(run_id, customer_id, document_name, action, has_mismatches, has_uncertain, created_at)
extraction_fields(id, run_id, field_name, value, confidence, uncertain)
validation_results(id, run_id, field_name, status, found, expected, rule_ref)
router_decisions(run_id, action, reasoning, amendment_email, created_at)

Examples:
"how many shipments flagged this week?" ->
SELECT COUNT(*) FROM pipeline_runs WHERE action != 'auto_approve' AND created_at >= date('now', '-7 days')

"show pending review for customer acme" ->
SELECT * FROM pipeline_runs WHERE customer_id = 'acme' AND action = 'flag_review'

"what fields failed most often?" ->
SELECT field_name, COUNT(*) as failures FROM validation_results WHERE status = 'mismatch' GROUP BY field_name ORDER BY failures DESC

When returning run records, include run_id in the selected columns so the UI can open run details.
""".strip()


def run_nl_query(question: str, settings: Settings) -> dict:
    init_db(settings.db_path)
    with trace_span(
        settings,
        name="natural-language-sql-query",
        input={"question": question},
        metadata={"feature": "nl-query"},
        tags=["feature:nl-query"],
    ) as span:
        prompt = f"""
{SCHEMA_PROMPT}

Given this schema and examples, write a single SELECT SQL query for: {question}. Return ONLY the SQL, nothing else.
""".strip()
        sql = _strip_fences(generate_text(settings, prompt, agent="query")).strip()
        _validate_select_sql(sql)
        sql = sql.rstrip(";").strip()

        with connect(settings.db_path) as connection:
            cursor = connection.execute(sql)
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description or []]
        result = {"sql": sql, "columns": columns, "rows": [list(row) for row in rows]}
        if span is not None:
            span.update(output={"sql": sql, "row_count": len(rows)})
        return result


def _validate_select_sql(sql: str) -> None:
    stripped = sql.strip()
    if not re.match(r"^select\b", stripped, flags=re.IGNORECASE):
        raise ValueError("Only SELECT queries allowed")
    if ";" in stripped.rstrip(";"):
        raise ValueError("Only one SELECT statement is allowed")


def _strip_fences(text: str) -> str:
    match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()
