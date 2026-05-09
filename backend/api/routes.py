from __future__ import annotations

import base64
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.config import get_settings
from backend.pipeline.graph import run_pipeline
from backend.pipeline.state import DocumentInput, PipelineState
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
        document=DocumentInput(
            filename=file.filename or "document",
            content_type=file.content_type or "application/octet-stream",
            content_base64=base64.b64encode(content).decode("ascii"),
            customer_id=customer_id,
        ),
    )
    result = run_pipeline(state, settings)
    if result.error:
        save_pipeline_run(result, settings.db_path)
    return {"run_id": run_id, "state": _state_response(result)}


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
    return list_runs(settings.db_path)


def _state_response(state: PipelineState) -> dict:
    data = state.model_dump(mode="json")
    if data.get("document"):
        data["document"] = {
            "filename": state.document.filename if state.document else None,
            "content_type": state.document.content_type if state.document else None,
            "customer_id": state.customer_id,
        }
    return data

