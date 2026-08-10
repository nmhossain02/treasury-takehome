import sys
from pathlib import Path

from fastapi.testclient import TestClient

from cola_mock.main import create_app


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "data"))

from build_public_cola_index import build  # noqa: E402


def test_search_is_ranked_and_does_not_create_persistent_search_state() -> None:
    app = create_app(testing=True)
    client = TestClient(app)
    response = client.post(
        "/mock/v1/applications/search",
        headers={"X-Demo-Session": "test-a"},
        json={
            "clues": [
                {"type": "brand_name", "value": "North Star", "confidence": 1, "evidence_ref": "i:s1"},
                {"type": "abv", "value": "45", "confidence": 1, "evidence_ref": "i:s2"},
                {"type": "net_contents_ml", "value": "750", "confidence": 1, "evidence_ref": "i:s3"},
            ]
        },
    )
    assert response.status_code == 200
    candidates = response.json()["candidates"]
    assert candidates[0]["application_id"] == "mock_ttb_002"
    state = app.state.store._states["test-a"]
    assert state.receipts == {}
    assert not hasattr(state, "searches")


def test_exact_identifier_does_not_fuzzily_match_neighboring_records() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/mock/v1/applications/search",
        json={
            "clues": [
                {
                    "type": "application_id",
                    "value": "MOCK TTB 001",
                    "confidence": 1,
                    "evidence_ref": "i:s1",
                }
            ]
        },
    )
    assert response.status_code == 200
    candidates = response.json()["candidates"]
    assert [candidate["application_id"] for candidate in candidates] == ["mock_ttb_001"]
    assert candidates[0]["score"] == 1


def test_public_sample_copy_is_searchable_from_observed_label_facts() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/mock/v1/applications/search",
        json={
            "clues": [
                {"type": "brand_name", "value": "Seven Fathoms", "confidence": .95, "evidence_ref": "front:1"},
                {"type": "class_type", "value": "Premium Rum", "confidence": .9, "evidence_ref": "front:2"},
                {"type": "country_of_origin", "value": "Cayman Islands", "confidence": .9, "evidence_ref": "back:1"},
                {"type": "abv", "value": "40", "confidence": .98, "evidence_ref": "front:3"},
                {"type": "net_contents_ml", "value": "750", "confidence": .98, "evidence_ref": "front:4"},
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["candidates"][0]["application_id"] == "sample_ttb_11038001000659"


def test_public_index_is_read_only_and_record_remains_searchable_after_local_decision(tmp_path: Path) -> None:
    index_path = tmp_path / "public-cola.sqlite3"
    build(ROOT / "fixtures" / "public-cola" / "records.lock.json", index_path)
    client = TestClient(create_app(index_path=index_path))
    headers = {"X-Demo-Session": "public-index-test"}
    search_body = {
        "clues": [
            {"type": "brand_name", "value": "Seven Fathoms", "confidence": .95, "evidence_ref": "front:1"},
            {"type": "country_of_origin", "value": "Cayman Islands", "confidence": .9, "evidence_ref": "back:1"},
            {"type": "abv", "value": "40", "confidence": .98, "evidence_ref": "front:3"},
            {"type": "net_contents_ml", "value": "750", "confidence": .98, "evidence_ref": "front:4"},
        ]
    }

    first = client.post("/mock/v1/applications/search", headers=headers, json=search_body)
    assert first.status_code == 200
    assert first.json()["candidates"][0]["application_id"] == "11038001000659"
    detail = client.get("/mock/v1/applications/11038001000659", headers=headers).json()
    assert detail["data_source"] == "ttb_public_registry"
    assert detail["registry_status"] == "surrendered"
    decision = client.post(
        "/mock/v1/applications/11038001000659/decisions",
        headers=headers,
        json={
            "verification_id": "ver_public",
            "decision": "approve",
            "reason_codes": [],
            "expected_status": "assigned",
            "expected_revision": 1,
            "idempotency_key": "public-decision-1",
        },
    )
    assert decision.status_code == 200

    second = client.post("/mock/v1/applications/search", headers=headers, json=search_body)
    assert second.status_code == 200
    assert second.json()["candidates"][0]["application_id"] == "11038001000659"
    assert client.get("/mock/v1/applications/11038001000659", headers=headers).json()["registry_status"] == "surrendered"


def test_partial_public_record_remains_searchable_without_invented_facts(tmp_path: Path) -> None:
    index_path = tmp_path / "public-cola.sqlite3"
    build(ROOT / "fixtures" / "public-cola" / "records.lock.json", index_path)
    client = TestClient(create_app(index_path=index_path))

    response = client.post(
        "/mock/v1/applications/search",
        json={
            "clues": [
                {
                    "type": "brand_name",
                    "value": "Dark Arts Whiskey House",
                    "confidence": .95,
                    "evidence_ref": "front:1",
                },
                {
                    "type": "class_type",
                    "value": "Straight Bourbon Whiskey",
                    "confidence": .95,
                    "evidence_ref": "front:2",
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["candidates"][0]["application_id"] == "24366001000234"
    detail = client.get("/mock/v1/applications/24366001000234").json()
    assert detail["facts"]["abv"] is None
    assert detail["facts"]["net_contents_ml"] is None


def test_decision_is_session_scoped_and_idempotent() -> None:
    client = TestClient(create_app(testing=True))
    body = {
        "verification_id": "ver_test",
        "decision": "approve",
        "reason_codes": [],
        "expected_status": "assigned",
        "expected_revision": 1,
        "idempotency_key": "decision-0001",
    }
    first = client.post(
        "/mock/v1/applications/mock_ttb_001/decisions",
        headers={"X-Demo-Session": "one"}, json=body,
    )
    repeat = client.post(
        "/mock/v1/applications/mock_ttb_001/decisions",
        headers={"X-Demo-Session": "one"}, json=body,
    )
    other = client.get(
        "/mock/v1/applications/mock_ttb_001", headers={"X-Demo-Session": "two"}
    )
    assert first.status_code == repeat.status_code == 200
    assert first.json() == repeat.json()
    assert first.json()["new_status"] == "approved"
    assert client.get(
        "/mock/v1/applications/mock_ttb_001", headers={"X-Demo-Session": "one"}
    ).json()["status"] == "assigned"
    assert other.json()["status"] == "assigned"


def test_separate_verifications_of_the_same_public_record_do_not_share_decision_state() -> None:
    client = TestClient(create_app(testing=True))
    headers = {"X-Demo-Session": "repeat-product"}
    first = client.post(
        "/mock/v1/applications/mock_ttb_001/decisions",
        headers=headers,
        json={
            "verification_id": "ver_first",
            "decision": "approve",
            "reason_codes": [],
            "expected_status": "assigned",
            "expected_revision": 1,
            "idempotency_key": "decision-repeat-1",
        },
    )
    second = client.post(
        "/mock/v1/applications/mock_ttb_001/decisions",
        headers=headers,
        json={
            "verification_id": "ver_second",
            "decision": "deny",
            "disposition": "needs_correction",
            "reason_codes": ["warning.text"],
            "expected_status": "assigned",
            "expected_revision": 1,
            "idempotency_key": "decision-repeat-2",
        },
    )

    assert first.status_code == second.status_code == 200
    assert first.json()["new_status"] == "approved"
    assert second.json()["new_status"] == "needs_correction"
    assert client.get(
        "/mock/v1/applications/mock_ttb_001", headers=headers
    ).json()["status"] == "assigned"


def test_one_verification_cannot_receive_two_different_decisions() -> None:
    client = TestClient(create_app(testing=True))
    headers = {"X-Demo-Session": "single-verification"}
    base = {
        "verification_id": "ver_once",
        "reason_codes": [],
        "expected_status": "assigned",
        "expected_revision": 1,
    }
    first = client.post(
        "/mock/v1/applications/mock_ttb_001/decisions",
        headers=headers,
        json={**base, "decision": "approve", "idempotency_key": "decision-once-1"},
    )
    second = client.post(
        "/mock/v1/applications/mock_ttb_001/decisions",
        headers=headers,
        json={**base, "decision": "approve", "idempotency_key": "decision-once-2"},
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "this verification already has a decision"


def test_stale_and_invalid_transitions_are_conflicts() -> None:
    client = TestClient(create_app())
    body = {
        "verification_id": "ver_test",
        "decision": "deny",
        "disposition": "rejected",
        "reason_codes": ["warning.text"],
        "expected_status": "assigned",
        "expected_revision": 1,
        "idempotency_key": "decision-0002",
    }
    response = client.post("/mock/v1/applications/mock_ttb_001/decisions", json=body)
    assert response.status_code == 409
