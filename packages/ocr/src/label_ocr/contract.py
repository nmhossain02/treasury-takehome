from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Protocol, runtime_checkable

BoundingBox = tuple[float, float, float, float]


class OcrStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class OcrImage:
    image_id: str
    content: bytes
    media_type: str

    def __post_init__(self) -> None:
        if not self.image_id.strip():
            raise ValueError("image_id must not be blank")
        if not self.content:
            raise ValueError("content must not be empty")
        if not self.media_type.strip():
            raise ValueError("media_type must not be blank")


@dataclass(frozen=True, slots=True)
class OcrRequest:
    images: tuple[OcrImage, ...]
    deadline_monotonic: float
    language_hints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "images", tuple(self.images))
        object.__setattr__(self, "language_hints", tuple(self.language_hints))
        if not self.images:
            raise ValueError("images must not be empty")
        image_ids = [image.image_id for image in self.images]
        if len(image_ids) != len(set(image_ids)):
            raise ValueError("image_id values must be unique within a request")
        if not math.isfinite(self.deadline_monotonic):
            raise ValueError("deadline_monotonic must be finite")
        if not all(hint.strip() for hint in self.language_hints):
            raise ValueError("language_hints must not contain blanks")


@dataclass(frozen=True, slots=True)
class TextSpan:
    text: str
    confidence: float
    image_id: str
    bbox: BoundingBox
    block_order: int
    line_order: int
    word_order: int

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("text must not be blank")
        if not math.isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not self.image_id.strip():
            raise ValueError("image_id must not be blank")
        if len(self.bbox) != 4:
            raise ValueError("bbox must contain x, y, width, height")
        x, y, width, height = self.bbox
        if any(
            not math.isfinite(value) or value < 0.0 or value > 1.0
            for value in self.bbox
        ):
            raise ValueError("bbox values must be normalized between 0 and 1")
        if x + width > 1.000001 or y + height > 1.000001:
            raise ValueError("bbox must fit within the normalized image")
        if min(self.block_order, self.line_order, self.word_order) < 0:
            raise ValueError("span ordering values must be non-negative")


@dataclass(frozen=True, slots=True)
class OcrOutcome:
    status: OcrStatus
    spans: tuple[TextSpan, ...] = ()
    warnings: tuple[str, ...] = ()
    error_codes: tuple[str, ...] = ()
    provider: str = ""
    version: str = ""
    timings: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "spans", tuple(self.spans))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "error_codes", tuple(self.error_codes))
        if not isinstance(self.status, OcrStatus):
            object.__setattr__(self, "status", OcrStatus(self.status))
        clean_timings = {str(key): float(value) for key, value in self.timings.items()}
        if any(
            not math.isfinite(value) or value < 0 for value in clean_timings.values()
        ):
            raise ValueError("timings must be non-negative")
        object.__setattr__(self, "timings", MappingProxyType(clean_timings))
        if self.status is OcrStatus.SUCCESS and self.error_codes:
            raise ValueError("successful outcomes cannot contain error codes")


@runtime_checkable
class OcrProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    async def recognize(self, request: OcrRequest) -> OcrOutcome: ...
