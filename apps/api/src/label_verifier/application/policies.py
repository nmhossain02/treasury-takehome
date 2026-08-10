from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from label_verifier.domain.models import VerificationSession

from .errors import ApplicationError


Candidate = dict[str, Any]


@dataclass(frozen=True)
class CandidateSelectionPolicy:
    """Select only candidates supported by sufficient evidence and rank separation."""

    automatic_match_threshold: float
    corroborated_match_threshold: float
    automatic_match_margin: float

    _CORROBORATING_SIGNALS: ClassVar[frozenset[str]] = frozenset(
        {
            "abv",
            "net_contents_ml",
            "country_of_origin",
            "responsible_party",
            "serial_number",
            "permit_number",
            "ttb_id",
            "application_id",
        }
    )

    def select(self, candidates: list[Candidate]) -> Candidate | None:
        """Return the top safe automatic match, or ``None`` for user confirmation."""

        if not candidates:
            return None

        top = candidates[0]
        required_score = (
            self.corroborated_match_threshold
            if self._is_strongly_corroborated(top)
            else self.automatic_match_threshold
        )
        runner_up_score = candidates[1]["score"] if len(candidates) > 1 else 0

        if top["score"] < required_score:
            return None
        if top["score"] - runner_up_score < self.automatic_match_margin:
            return None
        return top

    def _is_strongly_corroborated(self, candidate: Candidate) -> bool:
        signal_types = {
            signal["type"] for signal in candidate.get("supporting_signals", [])
        }
        conflicts = set(candidate.get("conflicting_signals", []))
        return (
            "brand_name" in signal_types
            and len(signal_types & self._CORROBORATING_SIGNALS) >= 3
            and conflicts <= {"class_type"}
        )


def validate_decision(
    session: VerificationSession,
    decision: dict[str, Any],
) -> None:
    """Reject decisions that conflict with the verification state or findings."""

    if session.application is None or session.result is None:
        raise ApplicationError(409, "confirm an application before making a decision")

    outcome = decision["decision"]
    findings_pass = session.result["overall_status"] == "pass"
    has_override = bool(decision.get("override_explanation"))

    if outcome == "approve" and not findings_pass and not has_override:
        raise ApplicationError(
            422,
            "approval of non-pass findings requires an override explanation",
        )
    if outcome == "deny" and not decision.get("reason_codes"):
        raise ApplicationError(422, "denial requires at least one reason code")
    if outcome == "deny" and findings_pass and not has_override:
        raise ApplicationError(
            422,
            "denial of pass findings requires an override explanation",
        )
