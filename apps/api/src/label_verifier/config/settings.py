from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    cola_mock_base_url: str = "http://127.0.0.1:8081"
    max_image_bytes: int = 1_500_000
    max_aggregate_bytes: int = 10_000_000
    max_decoded_pixels: int = 50_000_000
    max_request_concurrency: int = 1
    verification_ttl_seconds: int = 900
    request_deadline_seconds: float = 5.0
    automatic_match_threshold: float = 0.78
    corroborated_match_threshold: float = 0.68
    automatic_match_margin: float = 0.12
    ocr_strategies: tuple[str, ...] = ("tesseract",)
    ocr_tesseract_path: str = "tesseract"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_env=os.getenv("APP_ENV", cls.app_env),
            cola_mock_base_url=os.getenv("COLA_MOCK_BASE_URL", cls.cola_mock_base_url),
            max_image_bytes=int(os.getenv("MAX_IMAGE_BYTES", cls.max_image_bytes)),
            max_aggregate_bytes=int(os.getenv("MAX_AGGREGATE_BYTES", cls.max_aggregate_bytes)),
            max_decoded_pixels=int(os.getenv("MAX_DECODED_PIXELS", cls.max_decoded_pixels)),
            max_request_concurrency=max(1, int(os.getenv("MAX_REQUEST_CONCURRENCY", cls.max_request_concurrency))),
            verification_ttl_seconds=int(os.getenv("VERIFICATION_TTL_SECONDS", cls.verification_ttl_seconds)),
            request_deadline_seconds=float(
                os.getenv(
                    "REQUEST_DEADLINE_SECONDS",
                    str(float(os.getenv("VERIFICATION_DEADLINE_MS", "5000")) / 1000),
                )
            ),
            automatic_match_threshold=float(
                os.getenv("AUTOMATIC_MATCH_THRESHOLD", cls.automatic_match_threshold)
            ),
            corroborated_match_threshold=float(
                os.getenv("CORROBORATED_MATCH_THRESHOLD", cls.corroborated_match_threshold)
            ),
            automatic_match_margin=float(
                os.getenv("AUTOMATIC_MATCH_MARGIN", cls.automatic_match_margin)
            ),
            ocr_strategies=tuple(
                item.strip() for item in os.getenv("OCR_STRATEGIES", "tesseract").split(",") if item.strip()
            ),
            ocr_tesseract_path=os.getenv("OCR_TESSERACT_PATH", "tesseract"),
        )
