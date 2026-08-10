from __future__ import annotations

import pytest

from label_verifier.application.errors import ApplicationError
from label_verifier.application.policies import CandidateSelectionPolicy, validate_decision
from label_verifier.domain.models import (
    OcrBatch,
    ProcessingStatus,
    VerificationSession,
)


def policy() -> CandidateSelectionPolicy:
    return CandidateSelectionPolicy(
        automatic_match_threshold=0.78,
        corroborated_match_threshold=0.68,
        automatic_match_margin=0.12,
    )


def candidate(
    score: float,
    *signal_types: str,
    conflicts: list[str] | None = None,
) -> dict[str, object]:
    return {
        "application_id": "candidate-1",
        "score": score,
        "supporting_signals": [{"type": item} for item in signal_types],
        "conflicting_signals": conflicts or [],
    }


def session(overall_status: str | None) -> VerificationSession:
    item = VerificationSession(
        verification_id="verification-1",
        demo_session="demo-1",
        expires_at=100,
        spans=(),
        ocr=OcrBatch(ProcessingStatus.COMPLETE, ()),
        candidates=[],
    )
    if overall_status is not None:
        item.application = {"application_id": "application-1"}
        item.result = {"overall_status": overall_status}
    return item


def test_strong_corroboration_uses_the_lower_match_threshold() -> None:
    top = candidate(
        0.70,
        "brand_name",
        "abv",
        "net_contents_ml",
        "country_of_origin",
        conflicts=["class_type"],
    )

    assert policy().select([top]) == top


def test_sparse_evidence_requires_the_standard_match_threshold() -> None:
    assert policy().select([candidate(0.70, "brand_name")]) is None


def test_close_runner_up_prevents_automatic_selection() -> None:
    top = candidate(0.90, "brand_name")
    runner_up = {**candidate(0.80, "brand_name"), "application_id": "candidate-2"}

    assert policy().select([top, runner_up]) is None


def test_decision_requires_a_confirmed_application() -> None:
    with pytest.raises(ApplicationError, match="confirm an application") as raised:
        validate_decision(session(None), {"decision": "approve"})

    assert raised.value.status_code == 409


@pytest.mark.parametrize(
    ("overall_status", "decision", "expected_message"),
    [
        (
            "needs_review",
            {"decision": "approve"},
            "approval of non-pass findings requires an override explanation",
        ),
        (
            "needs_review",
            {"decision": "deny", "reason_codes": []},
            "denial requires at least one reason code",
        ),
        (
            "pass",
            {"decision": "deny", "reason_codes": ["other"]},
            "denial of pass findings requires an override explanation",
        ),
    ],
)
def test_decision_policy_explains_invalid_decisions(
    overall_status: str,
    decision: dict[str, object],
    expected_message: str,
) -> None:
    with pytest.raises(ApplicationError, match=expected_message):
        validate_decision(session(overall_status), decision)
