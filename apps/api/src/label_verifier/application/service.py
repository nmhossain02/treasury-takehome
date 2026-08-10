from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from label_verifier.adapters.cola import ColaGateway, ColaGatewayError
from label_verifier.adapters.ocr import OcrEngine
from label_verifier.config.settings import Settings
from label_verifier.domain.checks import applicability_plan, evaluate
from label_verifier.domain.identification import extract_clues
from label_verifier.domain.models import (
    IdentificationClue,
    IdentificationStatus,
    TransientImage,
    VerificationSession,
)

from .errors import ApplicationError
from .policies import CandidateSelectionPolicy, validate_decision
from .presenters import present_verification
from .sessions import InMemorySessionRepository


class VerificationService:
    """Orchestrate verification use cases across OCR, COLA, rules, and sessions."""

    def __init__(
        self,
        ocr: OcrEngine,
        cola: ColaGateway,
        sessions: InMemorySessionRepository,
        settings: Settings,
    ) -> None:
        self.ocr = ocr
        self.cola = cola
        self.sessions = sessions
        self.settings = settings
        self.candidate_policy = CandidateSelectionPolicy(
            automatic_match_threshold=settings.automatic_match_threshold,
            corroborated_match_threshold=settings.corroborated_match_threshold,
            automatic_match_margin=settings.automatic_match_margin,
        )

    async def create(
        self,
        images: tuple[TransientImage, ...],
        demo_session: str,
    ) -> dict[str, Any]:
        """Run OCR once, identify a COLA candidate, and evaluate an automatic match."""

        started = time.monotonic()
        deadline = started + self.settings.request_deadline_seconds

        ocr_started = time.monotonic()
        ocr = await self.ocr.recognize(images, deadline)
        ocr_ms = (time.monotonic() - ocr_started) * 1000

        clues = extract_clues(ocr.spans)
        candidates = await self._search_candidates(clues, demo_session)
        session = VerificationSession(
            verification_id=f"ver_{uuid4().hex}",
            demo_session=demo_session,
            expires_at=time.monotonic() + self.settings.verification_ttl_seconds,
            spans=ocr.spans,
            ocr=ocr,
            candidates=candidates,
        )

        automatic_match = self.candidate_policy.select(candidates)
        if automatic_match:
            await self._select(session, automatic_match["application_id"])
            identification = IdentificationStatus.MATCHED
        elif candidates:
            identification = IdentificationStatus.NEEDS_IDENTIFICATION
        else:
            identification = IdentificationStatus.NO_MATCH

        self.sessions.put(session)
        return self._present(
            session,
            identification,
            ocr_ms=round(ocr_ms, 2),
            total_ms=round((time.monotonic() - started) * 1000, 2),
        )

    async def confirm(
        self,
        verification_id: str,
        application_id: str,
        demo_session: str,
    ) -> dict[str, Any]:
        """Confirm a returned candidate and evaluate it using the retained OCR spans."""

        started = time.monotonic()
        session = self.sessions.get(verification_id, demo_session)
        candidate_ids = {item["application_id"] for item in session.candidates}
        if application_id not in candidate_ids:
            raise ApplicationError(
                422,
                "application was not a candidate for this verification",
            )

        await self._select(session, application_id)
        self.sessions.put(session)
        return self._present(
            session,
            IdentificationStatus.MATCHED,
            ocr_ms=0,
            total_ms=round((time.monotonic() - started) * 1000, 2),
        )

    async def decide(
        self,
        verification_id: str,
        body: dict[str, Any],
        demo_session: str,
    ) -> dict[str, Any]:
        """Validate and record a local decision for a completed verification."""

        session = self.sessions.get(verification_id, demo_session)
        validate_decision(session, body)
        application = session.application
        assert application is not None
        payload = {"verification_id": verification_id, **body}
        try:
            return await self.cola.decide(
                application["application_id"],
                payload,
                demo_session,
            )
        except ColaGatewayError as exc:
            raise ApplicationError(exc.status_code, exc.detail) from exc

    async def _search_candidates(
        self,
        clues: list[IdentificationClue],
        demo_session: str,
    ) -> list[dict[str, Any]]:
        if not clues:
            return []
        try:
            return await self.cola.search(
                [clue.__dict__ for clue in clues],
                demo_session,
            )
        except ColaGatewayError as exc:
            raise ApplicationError(exc.status_code, exc.detail) from exc

    async def _select(
        self,
        session: VerificationSession,
        application_id: str,
    ) -> None:
        try:
            application = await self.cola.get(application_id, session.demo_session)
        except ColaGatewayError as exc:
            raise ApplicationError(exc.status_code, exc.detail) from exc

        clues = extract_clues(session.spans)
        checks, overall_status = evaluate(application, session.spans, clues)
        session.application = application
        session.result = {
            "applicability_plan": applicability_plan(application),
            "checks": checks,
            "overall_status": overall_status,
        }

    @staticmethod
    def _present(
        session: VerificationSession,
        identification: IdentificationStatus,
        **timings: float,
    ) -> dict[str, Any]:
        return present_verification(
            session,
            identification,
            timings,
            now_monotonic=time.monotonic(),
        )
