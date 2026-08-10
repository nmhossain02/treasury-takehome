from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ApplicationStatus(StrEnum):
    RECEIVED = "received"
    ASSIGNED = "assigned"
    NEEDS_CORRECTION = "needs_correction"
    CORRECTED = "corrected"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApplicationFacts(BaseModel):
    brand_name: str
    fanciful_name: str | None = None
    class_type: str
    abv: float | None = Field(default=None, gt=0, le=100)
    net_contents_ml: int | None = Field(default=None, gt=0)
    responsible_party: str
    address: str
    imported: bool = False
    country_of_origin: str | None = None
    government_warning: str


class ApprovedPanel(BaseModel):
    panel_id: str
    panel_type: str
    width_inches: float
    height_inches: float
    text: str


class ColaApplication(BaseModel):
    application_id: str
    revision: int = Field(ge=1)
    status: ApplicationStatus
    registry_status: str | None = None
    registry_snapshot_date: str | None = None
    registry_detail_url: str | None = None
    data_source: Literal["synthetic", "ttb_public_registry"] = "synthetic"
    serial_number: str
    permit_number: str
    product_type: Literal["distilled_spirits"] = "distilled_spirits"
    source: Literal["domestic", "imported"]
    application_type: Literal["certificate_of_label_approval"] = "certificate_of_label_approval"
    applicant_name: str
    facts: ApplicationFacts
    aliases: list[str] = Field(default_factory=list)
    approved_panels: list[ApprovedPanel] = Field(default_factory=list)


class SearchClue(BaseModel):
    type: str = Field(min_length=1, max_length=40)
    value: str = Field(min_length=1, max_length=300)
    confidence: float = Field(ge=0, le=1)
    evidence_ref: str = Field(min_length=1, max_length=100)


class SearchRequest(BaseModel):
    normalization_version: Literal["identification.v1"] = "identification.v1"
    clues: list[SearchClue] = Field(min_length=1, max_length=100)
    limit: int = Field(default=3, ge=1, le=3)


class MatchSignal(BaseModel):
    type: str
    evidence_ref: str
    contribution: float


class Candidate(BaseModel):
    application_id: str
    revision: int
    status: ApplicationStatus
    score: float
    supporting_signals: list[MatchSignal]
    conflicting_signals: list[str]
    distinguishing_fields: dict[str, str | float | int | bool | None]


class SearchResponse(BaseModel):
    mock: Literal[True] = True
    scoring_version: Literal["cola-search.v1"] = "cola-search.v1"
    candidates: list[Candidate]


class DecisionRequest(BaseModel):
    verification_id: str = Field(min_length=1, max_length=100)
    decision: Literal["approve", "deny"]
    disposition: Literal["needs_correction", "rejected"] | None = None
    reason_codes: list[str] = Field(default_factory=list, max_length=20)
    notes: str | None = Field(default=None, max_length=1000)
    override_explanation: str | None = Field(default=None, max_length=1000)
    expected_status: ApplicationStatus
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=100)

    @field_validator("reason_codes")
    @classmethod
    def validate_reasons(cls, values: list[str]) -> list[str]:
        for value in values:
            if not value or len(value) > 100:
                raise ValueError("reason codes must contain 1 to 100 characters")
        return values


class DecisionReceipt(BaseModel):
    mock: Literal[True] = True
    receipt_id: str
    application_id: str
    decision: Literal["approve", "deny"]
    prior_status: ApplicationStatus
    new_status: ApplicationStatus
    revision: int
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
