from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, model_validator
from typing_extensions import TypedDict


class ExtractedField(BaseModel):
    value: Optional[str] = None
    confidence: float
    uncertain: bool = False
    source_snippet: Optional[str] = None

    @model_validator(mode="after")
    def flag_uncertain(self):
        if self.confidence < 0.5:
            self.uncertain = True
        return self


class ExtractionOutput(BaseModel):
    run_id: str
    invoice_number: ExtractedField
    consignee_name: ExtractedField
    hs_code: ExtractedField
    port_of_loading: ExtractedField
    port_of_discharge: ExtractedField
    incoterms: ExtractedField
    description_of_goods: ExtractedField
    gross_weight: ExtractedField


class FieldValidationResult(BaseModel):
    field_name: str
    status: Literal["match", "mismatch", "uncertain"]
    found: Optional[str] = None
    expected: Optional[str] = None
    rule_ref: Optional[str] = None


class ValidationOutput(BaseModel):
    run_id: str
    results: list[FieldValidationResult]
    has_mismatches: bool
    has_uncertain: bool


class RouterOutput(BaseModel):
    run_id: str
    action: Literal["auto_approve", "flag_review", "draft_amendment"]
    reasoning: str
    amendment_email: Optional[str] = None


class PipelineState(TypedDict):
    run_id: str
    document_bytes: bytes
    document_mime: str
    customer_id: str
    extraction: Optional[ExtractionOutput]
    document_extractions: Optional[list[dict]]
    validation: Optional[ValidationOutput]
    decision: Optional[RouterOutput]
    error: Optional[str]
