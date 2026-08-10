from __future__ import annotations

import asyncio
import re
from uuid import uuid4

from fastapi import FastAPI, File, Header, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse

from label_verifier.adapters.cola import ColaGateway, HttpColaGateway
from label_verifier.adapters.images import validate_images
from label_verifier.adapters.ocr import OcrEngine, build_ocr_engine
from label_verifier.api.schemas import DecisionBody, MatchConfirmation
from label_verifier.application.errors import ApplicationError
from label_verifier.application.service import VerificationService
from label_verifier.application.sessions import InMemorySessionRepository
from label_verifier.config.settings import Settings


SESSION_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,100}$")


def _session(value: str | None) -> str:
    if value is None:
        return f"demo_{uuid4().hex}"
    if not SESSION_PATTERN.fullmatch(value):
        raise HTTPException(status_code=400, detail="invalid X-Demo-Session")
    return value


def create_app(
    *,
    settings: Settings | None = None,
    ocr: OcrEngine | None = None,
    cola: ColaGateway | None = None,
    sessions: InMemorySessionRepository | None = None,
) -> FastAPI:
    """Compose the API with injectable adapters for production and integration tests."""

    settings = settings or Settings.from_env()
    ocr = ocr or build_ocr_engine(settings.ocr_strategies, settings.ocr_tesseract_path)
    cola = cola or HttpColaGateway(settings.cola_mock_base_url)
    sessions = sessions or InMemorySessionRepository()
    service = VerificationService(ocr, cola, sessions, settings)
    app = FastAPI(title="Alcohol Label Verifier", version="0.1.0")
    app.state.verification_service = service
    app.state.verification_slots = asyncio.Semaphore(settings.max_request_concurrency)

    @app.exception_handler(ApplicationError)
    async def application_error_handler(
        _request: Request,
        exc: ApplicationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.get("/health/live")
    async def live() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/health/ready")
    async def ready(response: Response) -> dict[str, object]:
        providers = getattr(ocr, "providers", (ocr,))
        provider_states = [
            {"provider": provider.name, "version": provider.version, "ready": provider.version != "unavailable"}
            for provider in providers
        ]
        provider_ready = any(state["ready"] for state in provider_states)
        if not provider_ready:
            response.status_code = 503
        return {
            "ready": provider_ready,
            "ocr": {
                "provider": ocr.name,
                "version": ocr.version,
                "ready": provider_ready,
                "strategies": provider_states,
            },
            "ruleset": "distilled-spirits.v1",
        }

    @app.get("/api/v1/capabilities")
    async def capabilities() -> dict[str, object]:
        return {
            "supported_categories": ["distilled_spirits"],
            "accepted_media_types": ["image/jpeg", "image/png"],
            "limits": {
                "max_image_bytes": settings.max_image_bytes,
                "max_aggregate_bytes": settings.max_aggregate_bytes,
                "max_decoded_pixels": settings.max_decoded_pixels,
                "semantic_image_count_limit": None,
                "processing_deadline_ms": int(settings.request_deadline_seconds * 1000),
            },
            # Stable convenience fields used by thin clients. The structured
            # limits object remains the canonical extensible representation.
            "max_file_bytes": settings.max_image_bytes,
            "max_aggregate_bytes": settings.max_aggregate_bytes,
            "ruleset": {"id": "distilled-spirits.v1", "version": "1.0.0"},
            "ocr_strategies": [
                {"id": strategy, "active": index == 0}
                for index, strategy in enumerate(getattr(ocr, "strategy_names", (ocr.name,)))
            ],
            "mock": False,
            "metadata_mode": "public_registry_snapshot",
            "decision_mode": "local",
        }

    @app.post("/api/v1/enforcement-items/verifications")
    async def verify(
        response: Response,
        images: list[UploadFile] = File(...),
        x_demo_session: str | None = Header(default=None),
    ) -> dict[str, object]:
        """Create a verification from one or more unordered label photos."""

        demo_session = _session(x_demo_session)
        response.headers["X-Demo-Session"] = demo_session
        accepted = await validate_images(images, settings)
        try:
            await asyncio.wait_for(app.state.verification_slots.acquire(), timeout=0.001)
        except TimeoutError:
            raise HTTPException(
                status_code=429,
                detail="verification capacity is busy; retry shortly",
                headers={"Retry-After": "2"},
            ) from None
        try:
            # Raw bytes remain referenced only by this call and are unreachable once recognize returns.
            return await service.create(accepted, demo_session)
        finally:
            app.state.verification_slots.release()

    @app.post("/api/v1/verifications/{verification_id}/application-match")
    async def confirm(
        verification_id: str,
        body: MatchConfirmation,
        response: Response,
        x_demo_session: str | None = Header(default=None),
    ) -> dict[str, object]:
        """Confirm a proposed COLA match without repeating OCR."""

        demo_session = _session(x_demo_session)
        response.headers["X-Demo-Session"] = demo_session
        return await service.confirm(verification_id, body.application_id, demo_session)

    @app.post("/api/v1/verifications/{verification_id}/decisions")
    async def decide(
        verification_id: str,
        body: DecisionBody,
        response: Response,
        x_demo_session: str | None = Header(default=None),
    ) -> dict[str, object]:
        """Record a validated approval or denial in local prototype state."""

        demo_session = _session(x_demo_session)
        response.headers["X-Demo-Session"] = demo_session
        return await service.decide(verification_id, body.model_dump(), demo_session)

    return app


app = create_app()
