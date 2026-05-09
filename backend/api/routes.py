from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.config import get_settings
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
    result = run_pipeline(state, settings)
    result["metadata"] = {"document_name": file.filename or "document"}  # type: ignore[typeddict-unknown-key]
    save_pipeline_run(result, settings.db_path)
    return {
        "run_id": run_id,
        "status": "error" if result.get("error") else "complete",
        "error": result.get("error"),
    }


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
    return run_nl_query(request.question, settings)


@router.get("/runs")
def runs() -> list[dict]:
    settings = get_settings(require_gemini=False)
    return list_runs(settings.db_path, limit=20)
