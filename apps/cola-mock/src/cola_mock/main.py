from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException

from .index import load_index
from .models import ColaApplication, DecisionReceipt, DecisionRequest, SearchRequest, SearchResponse
from .service import ColaStore


def _session(value: str | None) -> str:
    value = value or "anonymous-demo"
    if len(value) > 100 or not value.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="invalid X-Demo-Session")
    return value


def create_app(
    *, testing: bool = False, store: ColaStore | None = None, index_path: str | Path | None = None
) -> FastAPI:
    app = FastAPI(title="Mock COLA", version="0.1.0")
    configured_index = index_path or os.getenv("COLA_INDEX_PATH")
    index_metadata: dict[str, str] | None = None
    if store is not None:
        state = store
    elif configured_index:
        indexed, index_metadata = load_index(configured_index)
        state = ColaStore(lambda: deepcopy(indexed))
    else:
        state = ColaStore()
    app.state.store = state
    app.state.index_metadata = index_metadata

    @app.get("/health/live")
    async def live() -> dict[str, bool]:
        return {"ok": True, "mock": True}

    @app.get("/health/ready")
    async def ready() -> dict[str, bool]:
        return {
            "ready": True,
            "public_registry_index": index_metadata is not None,
            "local_decisions": True,
        }

    @app.post("/mock/v1/applications/search", response_model=SearchResponse)
    async def search(
        request: SearchRequest,
        x_demo_session: str | None = Header(default=None),
    ) -> SearchResponse:
        return state.search(_session(x_demo_session), request)

    @app.get("/mock/v1/applications/{application_id}", response_model=ColaApplication)
    async def detail(
        application_id: str,
        x_demo_session: str | None = Header(default=None),
    ) -> ColaApplication:
        return state.get(_session(x_demo_session), application_id)

    @app.get("/mock/v1/applications/{application_id}/panels/{panel_id}")
    async def panel(
        application_id: str,
        panel_id: str,
        x_demo_session: str | None = Header(default=None),
    ) -> dict[str, object]:
        application = state.get(_session(x_demo_session), application_id)
        for item in application.approved_panels:
            if item.panel_id == panel_id:
                return {"mock": True, **item.model_dump()}
        raise HTTPException(status_code=404, detail="mock panel not found")

    @app.post("/mock/v1/applications/{application_id}/decisions", response_model=DecisionReceipt)
    async def decision(
        application_id: str,
        request: DecisionRequest,
        x_demo_session: str | None = Header(default=None),
    ) -> DecisionReceipt:
        return state.decide(_session(x_demo_session), application_id, request)

    if testing or os.getenv("COLA_MOCK_TESTING") == "1":
        @app.post("/mock/v1/testing/reset")
        async def reset() -> dict[str, bool]:
            state.reset()
            return {"reset": True}

    return app


app = create_app()
