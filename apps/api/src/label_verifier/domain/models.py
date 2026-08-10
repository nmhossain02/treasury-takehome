from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ProcessingStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class IdentificationStatus(StrEnum):
    MATCHED = "matched"
    NEEDS_IDENTIFICATION = "needs_identification"
    NO_MATCH = "no_match"


class CheckStatus(StrEnum):
    PASS = "pass"
    MISMATCH = "mismatch"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class TransientImage:
    image_id: str
    content: bytes
    media_type: str
    width: int
    height: int


@dataclass(frozen=True)
class NormalizedSpan:
    text: str
    confidence: float
    image_id: str
    bbox: tuple[float, float, float, float]
    block_order: int = 0
    line_order: int = 0
    word_order: int = 0

    @property
    def evidence_ref(self) -> str:
        return f"{self.image_id}:{self.block_order}:{self.line_order}:{self.word_order}"


@dataclass(frozen=True)
class OcrBatch:
    status: ProcessingStatus
    spans: tuple[NormalizedSpan, ...]
    warnings: tuple[str, ...] = ()
    provider: str = ""
    version: str = ""
    timings: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class IdentificationClue:
    type: str
    value: str
    confidence: float
    evidence_ref: str


@dataclass
class VerificationSession:
    verification_id: str
    demo_session: str
    expires_at: float
    spans: tuple[NormalizedSpan, ...]
    ocr: OcrBatch
    candidates: list[dict[str, Any]]
    application: dict[str, Any] | None = None
    result: dict[str, Any] | None = None

