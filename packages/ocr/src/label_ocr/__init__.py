"""Stable public OCR contract and local provider implementations."""

from .contract import (
    BoundingBox,
    OcrImage,
    OcrOutcome,
    OcrProvider,
    OcrRequest,
    OcrStatus,
    TextSpan,
)
from .fixture import FixtureEntry, FixtureOcrProvider
from .tesseract import TesseractConfig, TesseractOcrProvider

__all__ = [
    "BoundingBox",
    "FixtureEntry",
    "FixtureOcrProvider",
    "OcrImage",
    "OcrOutcome",
    "OcrProvider",
    "OcrRequest",
    "OcrStatus",
    "TesseractConfig",
    "TesseractOcrProvider",
    "TextSpan",
]
