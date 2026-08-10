from __future__ import annotations

from typing import Any

from label_verifier.domain.models import IdentificationStatus, NormalizedSpan, VerificationSession


def present_verification(
    session: VerificationSession,
    identification: IdentificationStatus,
    timings: dict[str, float],
    *,
    now_monotonic: float,
) -> dict[str, Any]:
    """Build the stable public response from internal verification state."""

    result = session.result or {}
    application = _present_application(
        session.application,
        session.candidates,
        session.spans,
    )
    combined_timings = {**session.ocr.timings, **timings}

    return {
        "mock": False,
        "metadata_mode": "public_registry_snapshot",
        "decision_mode": "local",
        "verification_id": session.verification_id,
        "request_id": session.verification_id,
        "demo_session": session.demo_session,
        "processing_status": session.ocr.status.value,
        "identification_status": identification.value,
        "application": application,
        "matched_application": session.application,
        "candidates": [_present_candidate(item) for item in session.candidates[:3]],
        "applicability_plan": result.get("applicability_plan", []),
        "overall_status": result.get("overall_status"),
        "checks": _present_checks(result),
        "ruleset": {
            "id": "distilled-spirits.v1",
            "version": "1.0.0",
            "category": "distilled_spirits",
        },
        "ocr": {
            "provider": session.ocr.provider,
            "version": session.ocr.version,
            "strategies_attempted": [session.ocr.provider] if session.ocr.provider else [],
            "warnings": list(session.ocr.warnings),
        },
        "timing": combined_timings,
        "timings": combined_timings,
        "allowed_dispositions": _allowed_dispositions(application),
        "warnings": list(session.ocr.warnings),
        "expires_in_seconds": max(0, int(session.expires_at - now_monotonic)),
    }


def _present_checks(result: dict[str, Any]) -> list[dict[str, Any]]:
    applicability = {
        item["check_id"]: item for item in result.get("applicability_plan", [])
    }
    presented = []
    for check in result.get("checks", []):
        item = dict(check)
        plan_item = applicability.get(item["check_id"])
        if plan_item:
            item["applicability"] = {
                "status": plan_item["status"],
                "reason": plan_item["reason"],
            }
        presented.append(item)
    return presented


def _allowed_dispositions(application: dict[str, Any] | None) -> list[str]:
    if application is None:
        return []

    dispositions = ["needs_correction"]
    if application.get("decision_status", application["status"]) == "corrected":
        dispositions.append("rejected")
    return dispositions


def _present_application(
    application: dict[str, Any] | None,
    candidates: list[dict[str, Any]],
    spans: tuple[NormalizedSpan, ...],
) -> dict[str, Any] | None:
    if application is None:
        return None

    facts = application["facts"]
    candidate = next(
        (
            item
            for item in candidates
            if item["application_id"] == application["application_id"]
        ),
        {},
    )
    spans_by_ref = {span.evidence_ref: span for span in spans}
    match_evidence = []
    for signal in candidate.get("supporting_signals", []):
        evidence = spans_by_ref.get(signal.get("evidence_ref"))
        match_evidence.append({
            **signal,
            "value": evidence.text if evidence else None,
            "confidence": evidence.confidence if evidence else None,
        })

    return {
        "application_id": application["application_id"],
        "revision": application["revision"],
        "status": application.get("registry_status") or application["status"],
        "decision_status": application["status"],
        "registry_status": application.get("registry_status"),
        "registry_snapshot_date": application.get("registry_snapshot_date"),
        "registry_detail_url": application.get("registry_detail_url"),
        "data_source": application.get("data_source", "synthetic"),
        "brand_name": facts["brand_name"],
        "fanciful_name": facts.get("fanciful_name"),
        "class_type": facts["class_type"],
        "net_contents": (
            f'{facts["net_contents_ml"]:g} mL'
            if facts.get("net_contents_ml") is not None
            else None
        ),
        "alcohol_by_volume": (
            f'{facts["abv"]:g}% alc./vol.'
            if facts.get("abv") is not None
            else None
        ),
        "applicant_name": application["applicant_name"],
        "score": candidate.get("score"),
        "match_evidence": match_evidence,
    }


def _present_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    fields = candidate.get("distinguishing_fields", {})
    return {
        **candidate,
        "brand_name": fields.get("brand_name", candidate["application_id"]),
        "fanciful_name": fields.get("fanciful_name"),
        "class_type": fields.get("class_type"),
        "net_contents": (
            f'{fields["net_contents_ml"]:g} mL'
            if fields.get("net_contents_ml") is not None
            else None
        ),
        "alcohol_by_volume": (
            f'{fields["abv"]:g}% alc./vol.'
            if fields.get("abv") is not None
            else None
        ),
    }
