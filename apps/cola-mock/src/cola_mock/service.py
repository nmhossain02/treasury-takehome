from __future__ import annotations

import re
import threading
import unicodedata
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from uuid import uuid4

from fastapi import HTTPException

from .data import seeded_applications
from .models import (
    ApplicationStatus,
    Candidate,
    ColaApplication,
    DecisionReceipt,
    DecisionRequest,
    MatchSignal,
    SearchRequest,
    SearchResponse,
)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


WEIGHTS = {
    "application_id": 1.0,
    "ttb_id": 1.0,
    "serial_number": 0.85,
    "permit_number": 0.8,
    "brand_name": 0.42,
    "fanciful_name": 0.18,
    "class_type": 0.16,
    "abv": 0.12,
    "net_contents_ml": 0.12,
    "responsible_party": 0.10,
    "address": 0.08,
    "country_of_origin": 0.08,
    "text": 0.20,
}

EXACT_IDENTIFIER_TYPES = {"application_id", "ttb_id", "serial_number", "permit_number"}


def _fields(application: ColaApplication, clue_type: str) -> list[str]:
    facts = application.facts
    mapping: dict[str, list[str]] = {
        "application_id": [application.application_id],
        "ttb_id": [application.application_id],
        "serial_number": [application.serial_number],
        "permit_number": [application.permit_number],
        "brand_name": [facts.brand_name, *application.aliases],
        "fanciful_name": [facts.fanciful_name or ""],
        "class_type": [facts.class_type],
        "abv": [] if facts.abv is None else [f"{facts.abv:g}"],
        "net_contents_ml": [] if facts.net_contents_ml is None else [str(facts.net_contents_ml)],
        "responsible_party": [facts.responsible_party, application.applicant_name],
        "address": [facts.address],
        "country_of_origin": [facts.country_of_origin or ""],
    }
    if clue_type == "text":
        return [
            application.application_id, application.serial_number, application.permit_number,
            facts.brand_name, facts.fanciful_name or "", facts.class_type,
            facts.responsible_party, facts.address, facts.country_of_origin or "", *application.aliases,
        ]
    return mapping.get(clue_type, [])


def _similarity(query: str, candidate: str) -> float:
    left, right = normalize(query), normalize(candidate)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if len(left) >= 4 and (left in right or right in left):
        return 0.92
    return SequenceMatcher(None, left, right).ratio()


def score(application: ColaApplication, request: SearchRequest) -> Candidate | None:
    signals: list[MatchSignal] = []
    conflicts: list[str] = []
    # Only the strongest clue of each type contributes, preventing repeated photos from inflating a score.
    best_by_type: dict[str, tuple[float, str]] = {}
    for clue in request.clues:
        values = _fields(application, clue.type)
        if not values:
            continue
        if clue.type in EXACT_IDENTIFIER_TYPES:
            similarity = max(
                (1.0 if normalize(clue.value) == normalize(value) else 0.0 for value in values),
                default=0,
            )
        else:
            similarity = max((_similarity(clue.value, value) for value in values), default=0)
        weight = WEIGHTS.get(clue.type, 0)
        if similarity >= 0.82:
            contribution = weight * clue.confidence * similarity
            if contribution > best_by_type.get(clue.type, (0, ""))[0]:
                best_by_type[clue.type] = (contribution, clue.evidence_ref)
        elif clue.type != "text" and clue.confidence >= 0.8:
            conflicts.append(clue.type)
    for clue_type, (contribution, evidence_ref) in best_by_type.items():
        signals.append(MatchSignal(type=clue_type, evidence_ref=evidence_ref, contribution=round(contribution, 4)))
    conflicts = [clue_type for clue_type in conflicts if clue_type not in best_by_type]
    total = sum(item.contribution for item in signals)
    total -= min(0.25, 0.06 * len(set(conflicts)))
    total = round(max(0, min(1, total)), 4)
    if total < 0.18:
        return None
    return Candidate(
        application_id=application.application_id,
        revision=application.revision,
        status=application.status,
        score=total,
        supporting_signals=sorted(signals, key=lambda item: (-item.contribution, item.type)),
        conflicting_signals=sorted(set(conflicts)),
        distinguishing_fields={
            "brand_name": application.facts.brand_name,
            "fanciful_name": application.facts.fanciful_name,
            "class_type": application.facts.class_type,
            "abv": application.facts.abv,
            "net_contents_ml": application.facts.net_contents_ml,
            "country_of_origin": application.facts.country_of_origin,
            "registry_status": application.registry_status,
            "data_source": application.data_source,
        },
    )


@dataclass
class DemoState:
    applications: dict[str, ColaApplication]
    receipts: dict[str, tuple[DecisionRequest, DecisionReceipt]] = field(default_factory=dict)
    decisions_by_verification: dict[str, DecisionReceipt] = field(default_factory=dict)


class ColaStore:
    def __init__(self, application_factory: Callable[[], list[ColaApplication]] = seeded_applications) -> None:
        self._states: dict[str, DemoState] = {}
        self._lock = threading.RLock()
        self._application_factory = application_factory

    def _state(self, session: str) -> DemoState:
        with self._lock:
            if session not in self._states:
                self._states[session] = DemoState(
                    applications={item.application_id: item for item in self._application_factory()}
                )
            return self._states[session]

    def search(self, session: str, request: SearchRequest) -> SearchResponse:
        state = self._state(session)
        candidates = [
            candidate
            for app in state.applications.values()
            if (candidate := score(app, request)) is not None
        ]
        candidates.sort(key=lambda item: (-item.score, item.application_id))
        return SearchResponse(candidates=candidates[: request.limit])

    def get(self, session: str, application_id: str) -> ColaApplication:
        app = self._state(session).applications.get(application_id)
        if app is None:
            raise HTTPException(status_code=404, detail="mock application not found")
        return deepcopy(app)

    def decide(self, session: str, application_id: str, request: DecisionRequest) -> DecisionReceipt:
        with self._lock:
            state = self._state(session)
            existing = state.receipts.get(request.idempotency_key)
            if existing:
                original_request, receipt = existing
                if original_request == request:
                    return receipt
                raise HTTPException(status_code=409, detail="idempotency key was used for another decision")
            if request.verification_id in state.decisions_by_verification:
                raise HTTPException(status_code=409, detail="this verification already has a decision")
            app = state.applications.get(application_id)
            if app is None:
                raise HTTPException(status_code=404, detail="mock application not found")
            if app.status != request.expected_status or app.revision != request.expected_revision:
                raise HTTPException(status_code=409, detail="application status or revision is stale")
            if app.status not in {ApplicationStatus.ASSIGNED, ApplicationStatus.CORRECTED}:
                raise HTTPException(status_code=409, detail="application is not eligible for a decision")
            if request.decision == "approve":
                if request.disposition is not None:
                    raise HTTPException(status_code=422, detail="approval must not include a disposition")
                new_status = ApplicationStatus.APPROVED
            else:
                if not request.reason_codes:
                    raise HTTPException(status_code=422, detail="denial requires at least one reason code")
                disposition = request.disposition or "needs_correction"
                if disposition == "rejected" and app.status != ApplicationStatus.CORRECTED:
                    raise HTTPException(status_code=409, detail="only a corrected application is eligible for rejection")
                new_status = ApplicationStatus(disposition)
            prior = app.status
            receipt = DecisionReceipt(
                receipt_id=f"mock_receipt_{uuid4().hex}",
                application_id=application_id,
                decision=request.decision,
                prior_status=prior,
                new_status=new_status,
                revision=app.revision + 1,
            )
            state.receipts[request.idempotency_key] = (request, receipt)
            state.decisions_by_verification[request.verification_id] = receipt
            return receipt

    def reset(self) -> None:
        with self._lock:
            self._states.clear()
