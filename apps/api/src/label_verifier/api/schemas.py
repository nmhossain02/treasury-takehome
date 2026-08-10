from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class MatchConfirmation(BaseModel):
    application_id: str = Field(min_length=1, max_length=100)


class DecisionBody(BaseModel):
    decision: Literal["approve", "deny"]
    disposition: Literal["needs_correction", "rejected"] | None = None
    reason_codes: list[str] = Field(default_factory=list, max_length=20)
    notes: str | None = Field(default=None, max_length=1000)
    override_explanation: str | None = Field(default=None, max_length=1000)
    expected_status: Literal["assigned", "corrected"]
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=100)

    @field_validator("reason_codes")
    @classmethod
    def reason_lengths(cls, values: list[str]) -> list[str]:
        if any(not value or len(value) > 100 for value in values):
            raise ValueError("reason codes must contain 1 to 100 characters")
        return values

