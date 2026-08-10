from __future__ import annotations

from fastapi.testclient import TestClient

from label_verifier.application.sessions import InMemorySessionRepository
from label_verifier.config.settings import Settings
from label_verifier.main import create_app

from conftest import FakeColaGateway, StubOcr, png_bytes


def candidate(
    application_id: str,
    score: float,
    supporting_signals: list[dict[str, object]] | None = None,
    conflicting_signals: list[str] | None = None,
) -> dict[str, object]:
    return {
        "application_id": application_id,
        "revision": 1,
        "status": "assigned",
        "score": score,
        "supporting_signals": supporting_signals or [],
        "conflicting_signals": conflicting_signals or [],
        "distinguishing_fields": {"brand_name": "North Star"},
    }


def test_photos_only_auto_match_and_session_propagation(application: dict) -> None:
    ocr = StubOcr(["MOCK TTB 001", "North Star", "Straight Bourbon Whisky", "40% ALC/VOL", "750 mL"])
    gateway = FakeColaGateway([candidate("mock_ttb_001", .98)], {"mock_ttb_001": application})
    sessions = InMemorySessionRepository()
    client = TestClient(create_app(ocr=ocr, cola=gateway, sessions=sessions))

    response = client.post(
        "/api/v1/enforcement-items/verifications",
        headers={"X-Demo-Session": "browser-123"},
        files=[("images", ("view.png", png_bytes(), "image/png"))],
    )

    assert response.status_code == 200
    assert response.headers["X-Demo-Session"] == "browser-123"
    assert response.json()["identification_status"] == "matched"
    assert response.json()["matched_application"]["application_id"] == "mock_ttb_001"
    assert response.json()["application"]["brand_name"] == "North Star"
    assert response.json()["application"]["net_contents"] == "750 mL"
    assert response.json()["checks"][0]["id"] == response.json()["checks"][0]["check_id"]
    assert response.json()["timing"] == response.json()["timings"]
    assert gateway.search_sessions == ["browser-123"]
    stored = next(iter(sessions._items.values()))
    assert not hasattr(stored, "images")
    assert b"PNG" not in repr(stored).encode()


def test_ambiguous_confirmation_reuses_ocr_and_allows_denial(application: dict) -> None:
    second = {**application, "application_id": "mock_ttb_002"}
    ocr = StubOcr(["North Star", "Straight Bourbon Whisky", "40% ALC/VOL", "750 mL"])
    gateway = FakeColaGateway(
        [candidate("mock_ttb_001", .82), candidate("mock_ttb_002", .80)],
        {"mock_ttb_001": application, "mock_ttb_002": second},
    )
    client = TestClient(create_app(ocr=ocr, cola=gateway))
    headers = {"X-Demo-Session": "browser-456"}
    initial = client.post(
        "/api/v1/enforcement-items/verifications", headers=headers,
        files=[("images", ("view.png", png_bytes(), "image/png"))],
    )
    assert initial.json()["identification_status"] == "needs_identification"
    verification_id = initial.json()["verification_id"]
    confirmed = client.post(
        f"/api/v1/verifications/{verification_id}/application-match",
        headers=headers, json={"application_id": "mock_ttb_001"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["identification_status"] == "matched"
    assert ocr.calls == 1

    denied = client.post(
        f"/api/v1/verifications/{verification_id}/decisions",
        headers=headers,
        json={
            "decision": "deny", "disposition": "needs_correction",
            "reason_codes": ["government_warning"], "expected_status": "assigned",
            "expected_revision": 1, "idempotency_key": "decision-123",
        },
    )
    assert denied.status_code == 200
    assert denied.json()["new_status"] == "needs_correction"
    assert gateway.decision_sessions == ["browser-456"]


def test_corroborated_label_facts_can_match_despite_registry_class_vocabulary(application: dict) -> None:
    ocr = StubOcr(["Seven Fathoms", "40% ALC/VOL", "750 mL", "Cayman Islands"])
    signals = [
        {"type": clue_type, "evidence_ref": f"img:1:{index}", "contribution": .1}
        for index, clue_type in enumerate(
            ("brand_name", "abv", "net_contents_ml", "country_of_origin")
        )
    ]
    gateway = FakeColaGateway(
        [candidate("11038001000659", .70, signals, ["class_type"])],
        {"11038001000659": {**application, "application_id": "11038001000659"}},
    )
    client = TestClient(create_app(ocr=ocr, cola=gateway))

    response = client.post(
        "/api/v1/enforcement-items/verifications",
        files=[("images", ("view.png", png_bytes(), "image/png"))],
    )

    assert response.status_code == 200
    assert response.json()["identification_status"] == "matched"


def test_low_confidence_or_under_corroborated_candidate_still_requires_confirmation(application: dict) -> None:
    ocr = StubOcr(["North Star"])
    sparse_signals = [{"type": "brand_name", "evidence_ref": "img:1:0", "contribution": .42}]
    gateway = FakeColaGateway(
        [candidate("mock_ttb_001", .70, sparse_signals)],
        {"mock_ttb_001": application},
    )
    client = TestClient(create_app(ocr=ocr, cola=gateway))

    response = client.post(
        "/api/v1/enforcement-items/verifications",
        files=[("images", ("view.png", png_bytes(), "image/png"))],
    )

    assert response.status_code == 200
    assert response.json()["identification_status"] == "needs_identification"


def test_invalid_and_oversized_images_are_rejected_before_ocr(application: dict) -> None:
    ocr = StubOcr(["North Star"])
    gateway = FakeColaGateway([], {"mock_ttb_001": application})
    settings = Settings(max_image_bytes=50, max_aggregate_bytes=100)
    client = TestClient(create_app(settings=settings, ocr=ocr, cola=gateway))
    invalid = client.post(
        "/api/v1/enforcement-items/verifications",
        files=[("images", ("fake.png", b"not-an-image", "image/png"))],
    )
    too_large = client.post(
        "/api/v1/enforcement-items/verifications",
        files=[("images", ("view.png", png_bytes(), "image/png"))],
    )
    assert invalid.status_code == 415
    assert too_large.status_code == 413
    assert ocr.calls == 0


def test_capabilities_and_health_disclose_active_local_seam(application: dict) -> None:
    ocr = StubOcr([])
    gateway = FakeColaGateway([], {"mock_ttb_001": application})
    client = TestClient(create_app(ocr=ocr, cola=gateway))
    assert client.get("/health/live").json() == {"ok": True}
    assert client.get("/health/ready").json()["ocr"]["provider"] == "test-ocr"
    capabilities = client.get("/api/v1/capabilities").json()
    assert capabilities["limits"]["semantic_image_count_limit"] is None
    assert capabilities["max_file_bytes"] == capabilities["limits"]["max_image_bytes"]
    assert capabilities["max_aggregate_bytes"] == capabilities["limits"]["max_aggregate_bytes"]
    assert capabilities["accepted_media_types"] == ["image/jpeg", "image/png"]
    assert capabilities["mock"] is False
    assert capabilities["metadata_mode"] == "public_registry_snapshot"
    assert capabilities["decision_mode"] == "local"


def test_missing_verification_is_reported_as_an_api_error(application: dict) -> None:
    client = TestClient(
        create_app(
            ocr=StubOcr([]),
            cola=FakeColaGateway([], {"mock_ttb_001": application}),
        )
    )

    response = client.post(
        "/api/v1/verifications/missing/application-match",
        headers={"X-Demo-Session": "browser-789"},
        json={"application_id": "mock_ttb_001"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "verification not found or expired"}
