from __future__ import annotations

from backend.agents.cross_validator import CrossValidationResult, cross_validate
from backend.agents.extractor import extract_document
from backend.agents.router import decide_route
from backend.agents.validator import validate_extraction
from backend.config import Settings
from backend.pipeline.state import (
    ExtractedField,
    ExtractionOutput,
    FieldValidationResult,
    PipelineState,
    ValidationOutput,
)
from backend.storage.db import (
    load_ruleset,
    save_pipeline_run,
    save_shipment_documents,
    save_shipment_email,
    save_shipment_cross_validation,
)
from backend.trigger.models import ShipmentIngest


def ingest_shipment(ingest: ShipmentIngest, settings: Settings) -> PipelineState:
    if not ingest.attachments:
        raise ValueError("Shipment ingest requires at least one attachment")

    extractions = [
        extract_document(
            run_id=ingest.run_id,
            document_bytes=attachment.content,
            document_mime=attachment.mime_type,
            settings=settings,
        )
        for attachment in ingest.attachments
    ]
    document_names = [attachment.filename for attachment in ingest.attachments]
    merged_extraction = _merge_extractions(extractions)
    cross_validation = cross_validate(ingest.run_id, extractions, document_names)
    validation = validate_extraction(merged_extraction, load_ruleset(ingest.customer_id))
    validation = _with_cross_conflicts(validation, cross_validation)
    decision = decide_route(validation, settings)

    state = PipelineState(
        run_id=ingest.run_id,
        customer_id=ingest.customer_id,
        document_bytes=ingest.attachments[0].content,
        document_mime=ingest.attachments[0].mime_type,
        extraction=merged_extraction,
        document_extractions=[
            {
                "attachment_index": index,
                "filename": document_names[index],
                "extraction": extraction,
            }
            for index, extraction in enumerate(extractions)
        ],
        validation=validation,
        decision=decision,
        error=None,
    )
    state["metadata"] = {"document_name": ingest.attachments[0].filename}  # type: ignore[typeddict-unknown-key]

    save_pipeline_run(state, settings.db_path)
    save_shipment_cross_validation(ingest.run_id, cross_validation, settings.db_path)
    save_shipment_email(
        ingest.run_id,
        {
            "sender": ingest.sender,
            "reply_to": ingest.reply_to,
            "subject": ingest.subject,
            "message_id": ingest.message_id,
            "received_at": ingest.received_at.isoformat(),
        },
        settings.db_path,
    )
    save_shipment_documents(
        ingest.run_id,
        [
            {
                "attachment_index": index,
                "filename": attachment.filename,
                "mime": attachment.mime_type,
                "size": len(attachment.content),
            }
            for index, attachment in enumerate(ingest.attachments)
        ],
        settings.db_path,
    )
    return state


def _with_cross_conflicts(
    validation: ValidationOutput,
    cross_validation: CrossValidationResult,
) -> ValidationOutput:
    synthetic_rows = [
        FieldValidationResult(
            field_name=conflict.field_name,
            status="mismatch",
            found=_format_conflict_values(conflict.values),
            expected="All shipment documents agree",
            rule_ref="cross_doc_conflict",
        )
        for conflict in cross_validation.results
        if conflict.status == "conflict"
    ]
    if not synthetic_rows:
        return validation
    results = [*validation.results, *synthetic_rows]
    return ValidationOutput(
        run_id=validation.run_id,
        results=results,
        has_mismatches=True,
        has_uncertain=validation.has_uncertain,
    )


def _format_conflict_values(values: dict[str, str]) -> str:
    return " | ".join(f"{name}: {value}" for name, value in values.items())


def _merge_extractions(extractions: list[ExtractionOutput]) -> ExtractionOutput:
    if not extractions:
        raise ValueError("No extractions to merge")

    field_names = [
        "invoice_number",
        "consignee_name",
        "hs_code",
        "port_of_loading",
        "port_of_discharge",
        "incoterms",
        "description_of_goods",
        "gross_weight",
    ]

    merged_data: dict[str, str | ExtractedField] = {"run_id": extractions[0].run_id}
    for field_name in field_names:
        fields = [getattr(extraction, field_name) for extraction in extractions]
        non_null_fields = [field for field in fields if field.value is not None]

        if non_null_fields:
            best_field = max(non_null_fields, key=lambda field: field.confidence)
        else:
            best_field = max(fields, key=lambda field: field.confidence)

        merged_data[field_name] = best_field

    return ExtractionOutput.model_validate(merged_data)
