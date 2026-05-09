from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.config import get_settings
from backend.observability import flush_langfuse, trace_span
from backend.pipeline.graph import run_pipeline
from backend.pipeline.state import PipelineState
from backend.storage.db import get_run, list_runs, save_pipeline_run
from backend.storage.query import run_nl_query

router = APIRouter(prefix="/api")


class QueryRequest(BaseModel):
    question: str


@router.post("/pipeline/run")
async def start_pipeline(
    customer_id: str = Form(...),
    file: UploadFile = File(...),
) -> dict:
    settings = get_settings()
    content = await file.read()
    run_id = str(uuid.uuid4())
    state = PipelineState(
        run_id=run_id,
        customer_id=customer_id,
        document_bytes=content,
        document_mime=file.content_type or "application/octet-stream",
        extraction=None,
        validation=None,
        decision=None,
        error=None,
    )
    try:
        with trace_span(
            settings,
            name="trade-document-pipeline",
            input={
                "customer_id": customer_id,
                "document_name": file.filename or "document",
                "document_mime": state["document_mime"],
                "document_size_bytes": len(content),
            },
            session_id=run_id,
            metadata={"run_id": run_id, "customer_id": customer_id},
            tags=["feature:pipeline", f"customer:{customer_id}"],
        ) as span:
            result = run_pipeline(state, settings)
            result["metadata"] = {"document_name": file.filename or "document"}  # type: ignore[typeddict-unknown-key]
            save_pipeline_run(result, settings.db_path)
            response = {
                "run_id": run_id,
                "status": "error" if result.get("error") else "complete",
                "error": result.get("error"),
            }
            if span is not None:
                span.update(output=response)
            return response
    finally:
        flush_langfuse(settings)


@router.get("/pipeline/{run_id}")
def pipeline_run(run_id: str) -> dict:
    settings = get_settings(require_gemini=False)
    run = get_run(run_id, settings.db_path)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/query")
def query(request: QueryRequest) -> dict:
    settings = get_settings()
    try:
        return run_nl_query(request.question, settings)
    finally:
        flush_langfuse(settings)


@router.get("/runs")
def runs() -> list[dict]:
    settings = get_settings(require_gemini=False)
    return list_runs(settings.db_path, limit=20)
