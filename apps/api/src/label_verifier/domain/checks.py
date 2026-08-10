from __future__ import annotations

import re
from typing import Any

from .identification import normalize
from .models import CheckStatus, IdentificationClue, NormalizedSpan


WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink "
    "alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)


def _evidence_for(expected: str, spans: tuple[NormalizedSpan, ...]) -> list[dict[str, Any]]:
    expected_normalized = normalize(expected)
    evidence = []
    for span in spans:
        observed = normalize(span.text)
        if expected_normalized and (expected_normalized in observed or observed in expected_normalized):
            evidence.append({
                "evidence_ref": span.evidence_ref,
                "image_id": span.image_id,
                "text": span.text,
                "confidence": span.confidence,
                "bbox": span.bbox,
            })
    return evidence


def _result(
    check_id: str,
    label: str,
    status: CheckStatus,
    expected: Any,
    observed: Any,
    reason: str,
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": check_id, "check_id": check_id, "label": label, "status": status.value,
        "expected": expected, "observed": observed, "reason": reason,
        "evidence": evidence or [], "rule_references": ["distilled-spirits.v1"],
    }


def applicability_plan(application: dict[str, Any]) -> list[dict[str, str]]:
    """Describe which distilled-spirits checks apply to the matched application."""

    imported = bool(application["facts"]["imported"])
    has_abv = application["facts"].get("abv") is not None
    has_volume = application["facts"].get("net_contents_ml") is not None
    items = [
        ("brand_name", "applied", "Required distilled-spirits identity field."),
        ("class_type", "applied", "Required distilled-spirits identity field."),
        ("alcohol_content", "applied" if has_abv else "unable", "Expected ABV is present in the matched application." if has_abv else "The public record has no structured ABV."),
        ("net_contents", "applied" if has_volume else "unable", "Expected container volume is present in the matched application." if has_volume else "The public record has no structured container volume."),
        ("responsible_party", "applied", "Matched application supplies the responsible party."),
        ("country_of_origin", "applied" if imported else "skipped", "Required for imported products." if imported else "Domestic product."),
        ("government_warning", "applied", "Alcohol health warning is required."),
        ("same_field_of_vision", "unable", "Panel reconstruction is not reliable from arbitrary photos."),
        ("physical_format", "unable", "Photos do not provide trusted physical scale or bold metadata."),
    ]
    return [{"check_id": item[0], "status": item[1], "reason": item[2]} for item in items]


def evaluate(
    application: dict[str, Any], spans: tuple[NormalizedSpan, ...], clues: list[IdentificationClue]
) -> tuple[list[dict[str, Any]], str]:
    """Compare observed label evidence with COLA facts and return checks plus status."""

    facts = application["facts"]
    combined = " ".join(span.text for span in sorted(spans, key=lambda s: (s.image_id, s.block_order, s.line_order, s.word_order)))
    checks: list[dict[str, Any]] = []
    text_fields = [
        ("brand_name", "Brand name", facts["brand_name"]),
        ("class_type", "Class/type", facts["class_type"]),
        ("responsible_party", "Responsible party", facts["responsible_party"]),
    ]
    for check_id, label, expected in text_fields:
        evidence = _evidence_for(expected, spans)
        status = CheckStatus.PASS if evidence else CheckStatus.NEEDS_REVIEW
        reason = "Expected text was observed." if evidence else "Expected text was not read with enough confidence."
        checks.append(_result(check_id, label, status, expected, evidence[0]["text"] if evidence else None, reason, evidence))

    observed_abv = [float(clue.value) for clue in clues if clue.type == "abv"]
    expected_abv = facts.get("abv")
    if expected_abv is None:
        abv_status, abv_reason = CheckStatus.NEEDS_REVIEW, "The public record has no structured ABV to compare."
    elif any(abs(value - float(expected_abv)) < 0.01 for value in observed_abv):
        abv_status, abv_reason = CheckStatus.PASS, "Observed ABV equals the application."
    elif observed_abv:
        abv_status, abv_reason = CheckStatus.MISMATCH, "Observed ABV conflicts with the application."
    else:
        abv_status, abv_reason = CheckStatus.NEEDS_REVIEW, "No reliable ABV was observed."
    checks.append(_result("alcohol_content", "Alcohol content", abv_status, expected_abv, observed_abv or None, abv_reason))

    observed_ml = [int(float(clue.value)) for clue in clues if clue.type == "net_contents_ml"]
    expected_ml = facts.get("net_contents_ml")
    if expected_ml is None:
        volume_status, volume_reason = CheckStatus.NEEDS_REVIEW, "The public record has no structured net contents to compare."
    elif int(expected_ml) in observed_ml:
        volume_status, volume_reason = CheckStatus.PASS, "Observed net contents equal the application."
    elif observed_ml:
        volume_status, volume_reason = CheckStatus.MISMATCH, "Observed net contents conflict with the application."
    else:
        volume_status, volume_reason = CheckStatus.NEEDS_REVIEW, "No reliable net contents were observed."
    checks.append(_result("net_contents", "Net contents", volume_status, expected_ml, observed_ml or None, volume_reason))

    if facts["imported"]:
        expected_country = facts.get("country_of_origin")
        country_evidence = _evidence_for(expected_country, spans) if expected_country else []
        country_status = CheckStatus.PASS if country_evidence else CheckStatus.NEEDS_REVIEW
        checks.append(_result(
            "country_of_origin", "Country of origin", country_status, expected_country,
            country_evidence[0]["text"] if country_evidence else None,
            "Expected origin was observed." if country_evidence else "Imported product origin was not reliably observed.",
            country_evidence,
        ))

    expected_warning = normalize(WARNING)
    normalized_combined = normalize(combined)
    warning_present = "government warning" in normalized_combined
    if expected_warning in normalized_combined:
        warning_status, warning_reason = CheckStatus.PASS, "The complete required warning was observed."
    elif warning_present:
        warning_status, warning_reason = CheckStatus.MISMATCH, "A warning was observed but its text is incomplete or differs."
    else:
        warning_status, warning_reason = CheckStatus.NEEDS_REVIEW, "The warning was not reliably observed."
    checks.append(_result("government_warning", "Government warning", warning_status, WARNING, None, warning_reason))
    checks.append(_result(
        "same_field_of_vision", "Same field of vision", CheckStatus.NEEDS_REVIEW, None, None,
        "Arbitrary photos do not yet establish a reliable approved-panel reconstruction.",
    ))
    checks.append(_result(
        "physical_format", "Physical format", CheckStatus.NEEDS_REVIEW, None, None,
        "Type size, bold treatment, and contrast need trusted scale or richer image metadata.",
    ))

    statuses = {item["status"] for item in checks}
    overall = "mismatch" if "mismatch" in statuses else "needs_review" if "needs_review" in statuses else "pass"
    return checks, overall
