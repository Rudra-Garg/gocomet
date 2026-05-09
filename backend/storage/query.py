from __future__ import annotations

import re

from backend.agents.gemini import generate_text
from backend.config import Settings
from backend.storage.db import connect, init_db


def run_nl_query(question: str, settings: Settings) -> dict:
    init_db(settings.db_path)
    prompt = f"""
Generate one SQLite SELECT statement for this database.

Tables:
- pipeline_runs(run_id, customer_id, action, error, created_at, updated_at)
- extracted_fields(id, run_id, name, value, confidence, source_text)
- validation_results(id, run_id, field, expected, actual, status, confidence, message)
- router_decisions(run_id, action, reasoning, amendment_email)

Question: {question}

Return only SQL. Do not use markdown.
""".strip()
    sql = _strip_fences(generate_text(settings, prompt)).strip().rstrip(";")
    if not re.match(r"^\s*select\b", sql, flags=re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed")
    if ";" in sql:
        raise ValueError("Only one SELECT statement is allowed")

    with connect(settings.db_path) as connection:
        cursor = connection.execute(sql)
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description or []]
    return {"sql": sql, "columns": columns, "rows": [list(row) for row in rows]}


def _strip_fences(text: str) -> str:
    match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()

