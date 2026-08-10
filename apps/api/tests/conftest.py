from __future__ import annotations

import io
from typing import Any

import pytest
from PIL import Image

from label_verifier.domain.models import NormalizedSpan, OcrBatch, ProcessingStatus, TransientImage


def png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (24, 24), "white").save(output, format="PNG")
    return output.getvalue()


class StubOcr:
    name = "test-ocr"
    version = "1"

    def __init__(self, lines: list[str]) -> None:
        self.lines = lines
        self.calls = 0

    async def recognize(self, images: tuple[TransientImage, ...], deadline_monotonic: float) -> OcrBatch:
        self.calls += 1
        return OcrBatch(
            ProcessingStatus.COMPLETE,
            tuple(
                NormalizedSpan(line, 0.99, images[index % len(images)].image_id, (0, 0, 1, 0.1), 0, index, 0)
                for index, line in enumerate(self.lines)
            ),
            provider=self.name,
            version=self.version,
        )


class FakeColaGateway:
    def __init__(self, candidates: list[dict[str, Any]], applications: dict[str, dict[str, Any]]) -> None:
        self.candidates = candidates
        self.applications = applications
        self.search_sessions: list[str] = []
        self.decision_sessions: list[str] = []

    async def search(self, clues: list[dict[str, Any]], demo_session: str) -> list[dict[str, Any]]:
        assert all("content" not in clue and "image" not in clue for clue in clues)
        self.search_sessions.append(demo_session)
        return self.candidates

    async def get(self, application_id: str, demo_session: str) -> dict[str, Any]:
        return self.applications[application_id]

    async def decide(self, application_id: str, body: dict[str, Any], demo_session: str) -> dict[str, Any]:
        self.decision_sessions.append(demo_session)
        return {
            "mock": True,
            "receipt_id": "mock_receipt_test",
            "application_id": application_id,
            "decision": body["decision"],
            "prior_status": body["expected_status"],
            "new_status": "needs_correction" if body["decision"] == "deny" else "approved",
            "revision": body["expected_revision"] + 1,
            "decided_at": "2026-08-06T20:00:00Z",
        }


@pytest.fixture
def application() -> dict[str, Any]:
    return {
        "application_id": "mock_ttb_001",
        "revision": 1,
        "status": "assigned",
        "serial_number": "2026-001",
        "permit_number": "DSP-KY-0001",
        "product_type": "distilled_spirits",
        "source": "domestic",
        "application_type": "certificate_of_label_approval",
        "applicant_name": "Example Spirits Company",
        "facts": {
            "brand_name": "North Star",
            "fanciful_name": "Reserve",
            "class_type": "Straight Bourbon Whisky",
            "abv": 40,
            "net_contents_ml": 750,
            "responsible_party": "Example Spirits Company",
            "address": "100 Market Street, Louisville, KY 40202",
            "imported": False,
            "country_of_origin": None,
            "government_warning": "required warning",
        },
        "aliases": [],
        "approved_panels": [],
    }

