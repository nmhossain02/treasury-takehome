from __future__ import annotations

import asyncio
import hashlib
import time
from collections.abc import Mapping
from dataclasses import dataclass

from .contract import OcrOutcome, OcrRequest, OcrStatus, TextSpan


@dataclass(frozen=True, slots=True)
class FixtureEntry:
    """Fixture for one image digest.

    Span image IDs are replaced with the request image ID. `delay_seconds` is
    useful for deterministic deadline and partial-result tests.
    """

    spans: tuple[TextSpan, ...] = ()
    delay_seconds: float = 0.0
    error_code: str | None = None
    warning: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "spans", tuple(self.spans))
        if self.delay_seconds < 0:
            raise ValueError("delay_seconds must be non-negative")


class FixtureOcrProvider:
    def __init__(
        self, fixtures: Mapping[str, FixtureEntry], *, version: str = "1"
    ) -> None:
        self._fixtures = dict(fixtures)
        self._version = version

    @property
    def name(self) -> str:
        return "fixture-sha256"

    @property
    def version(self) -> str:
        return self._version

    async def recognize(self, request: OcrRequest) -> OcrOutcome:
        started = time.monotonic()
        spans: list[TextSpan] = []
        warnings: list[str] = []
        errors: list[str] = []
        completed = 0

        for image in request.images:
            remaining = request.deadline_monotonic - time.monotonic()
            if remaining <= 0:
                errors.append("deadline_exceeded")
                break
            digest = hashlib.sha256(image.content).hexdigest()
            fixture = self._fixtures.get(digest)
            if fixture is None:
                errors.append("fixture_not_found")
                continue
            if fixture.delay_seconds:
                try:
                    await asyncio.wait_for(
                        asyncio.sleep(fixture.delay_seconds), timeout=remaining
                    )
                except asyncio.TimeoutError:
                    errors.append("deadline_exceeded")
                    break
            if fixture.warning:
                warnings.append(fixture.warning)
            if fixture.error_code:
                errors.append(fixture.error_code)
                continue
            spans.extend(
                TextSpan(
                    text=span.text,
                    confidence=span.confidence,
                    image_id=image.image_id,
                    bbox=span.bbox,
                    block_order=span.block_order,
                    line_order=span.line_order,
                    word_order=span.word_order,
                )
                for span in fixture.spans
            )
            completed += 1

        if not errors:
            status = OcrStatus.SUCCESS
        elif completed or spans:
            status = OcrStatus.PARTIAL
        else:
            status = OcrStatus.FAILED
        elapsed_ms = (time.monotonic() - started) * 1000.0
        return OcrOutcome(
            status=status,
            spans=tuple(spans),
            warnings=tuple(dict.fromkeys(warnings)),
            error_codes=tuple(dict.fromkeys(errors)),
            provider=self.name,
            version=self.version,
            timings={"total_ms": elapsed_ms},
        )
