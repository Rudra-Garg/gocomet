from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RouterAction(str, Enum):
    AUTO_APPROVE = "auto_approve"
    DRAFT_AMENDMENT = "draft_amendment"
    FLAG_REVIEW = "flag_review"


class ValidationStatus(str, Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    UNCERTAIN = "uncertain"
    NO_RULE = "no_rule"


class DocumentInput(BaseModel):
    filename: str
    content_type: str
    content_base64: str
    customer_id: str


class ExtractedField(BaseModel):
    name: str
    value: str | None = None
    confidence: float = Field(ge=0, le=1)
    source_text: str | None = None


class ExtractionResult(BaseModel):
    fields: list[ExtractedField]
    summary: str | None = None


class ValidationItem(BaseModel):
    field: str
    expected: str | None = None
    actual: str | None = None
    status: ValidationStatus
    confidence: float = Field(ge=0, le=1)
    message: str


class ValidationResult(BaseModel):
    items: list[ValidationItem]
    matched_count: int = 0
    mismatched_count: int = 0
    uncertain_count: int = 0
    no_rule_count: int = 0


class RouterDecision(BaseModel):
    action: RouterAction
    reasoning: str
    amendment_email: str | None = None


class PipelineState(BaseModel):
    run_id: str
    customer_id: str
    document: DocumentInput | None = None
    extraction: ExtractionResult | None = None
    validation: ValidationResult | None = None
    decision: RouterDecision | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)
