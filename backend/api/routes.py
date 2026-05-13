from __future__ import annotations

import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.config import PROJECT_ROOT, get_settings
from backend.observability import flush_langfuse, trace_span
from backend.pipeline.graph import run_pipeline
from backend.pipeline.multi import ingest_shipment
from backend.pipeline.state import PipelineState
from backend.storage.db import (
    get_run,
    get_shipment_email,
    list_inbox,
    list_runs,
    save_pipeline_run,
    save_shipment_reply,
)
from backend.storage.query import run_nl_query
from backend.trigger.models import ShipmentAttachment, ShipmentIngest
from backend.trigger.smtp_sender import send_reply

router = APIRouter(prefix="/api")


class QueryRequest(BaseModel):
    question: str


class SimulateTriggerRequest(BaseModel):
    customer_id: str
    filenames: list[str]


class SendReplyRequest(BaseModel):
    body: str


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
            result["document_extractions"] = [
                {
                    "attachment_index": 0,
                    "filename": file.filename or "document",
                    "extraction": result["extraction"],
                }
            ]
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


@router.get("/inbox")
def get_inbox() -> list[dict]:
    settings = get_settings(require_gemini=False)
    return list_inbox(settings.db_path)


@router.post("/trigger/simulate")
def simulate_trigger(request: SimulateTriggerRequest) -> dict:
    if not request.filenames:
        raise HTTPException(status_code=400, detail="At least one filename is required")

    sample_dir = PROJECT_ROOT / "data" / "sample_docs"
    attachments = [
        ShipmentAttachment(
            filename=path.name,
            mime_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            content=path.read_bytes(),
        )
        for path in (_safe_sample_path(sample_dir, filename) for filename in request.filenames)
    ]
    settings = get_settings()
    run_id = str(uuid.uuid4())
    ingest = ShipmentIngest(
        run_id=run_id,
        customer_id=request.customer_id,
        sender="simulation@example.com",
        reply_to="simulation@example.com",
        subject="Simulated shipment documents",
        message_id=f"simulate-{run_id}",
        received_at=datetime.now(timezone.utc),
        attachments=attachments,
    )
    ingest_shipment(ingest, settings)
    return {"run_id": run_id}


@router.get("/shipments/{run_id}/email")
def shipment_email(run_id: str) -> dict:
    settings = get_settings(require_gemini=False)
    metadata = get_shipment_email(run_id, settings.db_path)
    if metadata is None:
        raise HTTPException(status_code=404, detail="Shipment email not found")
    return {"reply_to": metadata["reply_to"], "subject": metadata["subject"]}


@router.post("/shipments/{run_id}/send-reply")
def shipment_send_reply(run_id: str, request: SendReplyRequest) -> dict:
    settings = get_settings(require_gemini=False)
    metadata = get_shipment_email(run_id, settings.db_path)
    if metadata is None:
        raise HTTPException(status_code=404, detail="Shipment email not found")
    sent_subject = send_reply(
        settings,
        to=metadata["reply_to"],
        subject=metadata["subject"],
        body=request.body,
    )
    save_shipment_reply(
        run_id,
        sent_to=metadata["reply_to"],
        subject=sent_subject,
        body=request.body,
        db_path=settings.db_path,
    )
    return {"sent": True, "sent_to": metadata["reply_to"]}


def _safe_sample_path(sample_dir: Path, filename: str) -> Path:
    candidate = Path(filename)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise HTTPException(status_code=400, detail="Invalid sample filename")
    path = (sample_dir / candidate).resolve()
    root = sample_dir.resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Sample document not found: {filename}")
    return path
