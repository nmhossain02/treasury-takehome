from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol

from label_verifier.domain.models import NormalizedSpan, OcrBatch, ProcessingStatus, TransientImage


class OcrEngine(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    async def recognize(self, images: tuple[TransientImage, ...], deadline_monotonic: float) -> OcrBatch: ...


class LabelOcrAdapter:
    """The sole dependency point for the shared ``label_ocr`` package."""

    def __init__(self, provider: Any) -> None:
        self._provider = provider

    @property
    def name(self) -> str:
        return str(self._provider.name)

    @property
    def version(self) -> str:
        return str(self._provider.version)

    async def recognize(self, images: tuple[TransientImage, ...], deadline_monotonic: float) -> OcrBatch:
        # Import lazily so application and API tests can inject a lightweight provider.
        from label_ocr import OcrImage, OcrRequest

        request = OcrRequest(
            images=tuple(
                OcrImage(image_id=image.image_id, content=image.content, media_type=image.media_type)
                for image in images
            ),
            deadline_monotonic=deadline_monotonic,
            language_hints=("eng",),
        )
        outcome = await self._provider.recognize(request)
        status = "complete" if outcome.status.value == "success" else outcome.status.value
        warnings = [*outcome.warnings, *(f"OCR issue: {code}" for code in outcome.error_codes)]
        return OcrBatch(
            status=ProcessingStatus(status),
            spans=tuple(
                NormalizedSpan(
                    text=span.text,
                    confidence=span.confidence,
                    image_id=span.image_id,
                    bbox=tuple(span.bbox),
                    block_order=span.block_order,
                    line_order=span.line_order,
                    word_order=span.word_order,
                )
                for span in outcome.spans
            ),
            warnings=tuple(dict.fromkeys(warnings)),
            provider=outcome.provider or self.name,
            version=outcome.version or self.version,
            timings=dict(outcome.timings),
        )


class OcrStrategyRouter:
    """Ordered fallback policy; provider details stop at this adapter boundary."""

    def __init__(self, providers: tuple[OcrEngine, ...]) -> None:
        if not providers:
            raise ValueError("at least one OCR provider is required")
        self.providers = providers

    @property
    def name(self) -> str:
        return self.providers[0].name

    @property
    def version(self) -> str:
        return self.providers[0].version

    @property
    def strategy_names(self) -> tuple[str, ...]:
        return tuple(provider.name for provider in self.providers)

    async def recognize(self, images: tuple[TransientImage, ...], deadline_monotonic: float) -> OcrBatch:
        warnings: list[str] = []
        last: OcrBatch | None = None
        attempts = 0
        for provider in self.providers:
            if time.monotonic() >= deadline_monotonic:
                break
            attempts += 1
            outcome = await provider.recognize(images, deadline_monotonic)
            warnings.extend(outcome.warnings)
            last = outcome
            if outcome.status != ProcessingStatus.FAILED:
                return OcrBatch(
                    outcome.status, outcome.spans, tuple(dict.fromkeys(warnings)),
                    outcome.provider, outcome.version,
                    {**outcome.timings, "strategy_attempt_count": float(attempts)},
                )
        if last is None:
            return OcrBatch(ProcessingStatus.FAILED, (), ("OCR deadline exhausted",))
        return OcrBatch(
            last.status, last.spans, tuple(dict.fromkeys(warnings)), last.provider, last.version,
            {**last.timings, "strategy_attempt_count": float(attempts)},
        )


def build_ocr_engine(strategy_ids: tuple[str, ...], tesseract_path: str) -> OcrStrategyRouter:
    if len(strategy_ids) != len(set(strategy_ids)):
        raise RuntimeError("OCR strategies must not contain duplicates")
    providers: list[OcrEngine] = []
    for strategy_id in strategy_ids:
        if strategy_id == "fake":
            providers.append(DemoOcrProvider())
        elif strategy_id == "tesseract":
            try:
                from label_ocr import TesseractConfig, TesseractOcrProvider
            except ImportError as exc:
                raise RuntimeError(
                    "OCR_STRATEGIES includes tesseract but the label_ocr package is unavailable"
                ) from exc
            provider = TesseractOcrProvider(TesseractConfig(executable=tesseract_path))
            providers.append(LabelOcrAdapter(provider))
        else:
            raise RuntimeError(f"unsupported OCR strategy: {strategy_id}")
    return OcrStrategyRouter(tuple(providers))


@dataclass
class DemoOcrProvider:
    """Development-only deterministic seam; real deployments inject ``LabelOcrAdapter``."""

    fixture_text: tuple[str, ...] = (
        "MOCK TTB 001", "North Star", "Reserve", "Straight Bourbon Whisky", "40% ALC/VOL", "750 mL",
    )

    @property
    def name(self) -> str:
        return "demo-fixture"

    @property
    def version(self) -> str:
        return "1"

    async def recognize(self, images: tuple[TransientImage, ...], deadline_monotonic: float) -> OcrBatch:
        if time.monotonic() >= deadline_monotonic:
            return OcrBatch(ProcessingStatus.FAILED, (), ("OCR deadline exhausted",), self.name, self.version)
        image_id = images[0].image_id
        spans = tuple(
            NormalizedSpan(text, 0.99, image_id, (0.05, 0.05 + index * 0.07, 0.9, 0.05), 0, index, 0)
            for index, text in enumerate(self.fixture_text)
        )
        return OcrBatch(ProcessingStatus.COMPLETE, spans, provider=self.name, version=self.version)
