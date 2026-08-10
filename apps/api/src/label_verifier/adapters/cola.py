from __future__ import annotations

from typing import Any, Protocol

import httpx


class ColaGateway(Protocol):
    async def search(self, clues: list[dict[str, Any]], demo_session: str) -> list[dict[str, Any]]: ...
    async def get(self, application_id: str, demo_session: str) -> dict[str, Any]: ...
    async def decide(self, application_id: str, body: dict[str, Any], demo_session: str) -> dict[str, Any]: ...


class ColaGatewayError(RuntimeError):
    def __init__(self, status_code: int, detail: Any) -> None:
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


class HttpColaGateway:
    def __init__(self, base_url: str, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._transport = transport

    async def _request(self, method: str, path: str, session: str, **kwargs: Any) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, transport=self._transport, timeout=httpx.Timeout(2.0, connect=0.5)
            ) as client:
                response = await client.request(method, path, headers={"X-Demo-Session": session}, **kwargs)
        except httpx.HTTPError as exc:
            raise ColaGatewayError(503, "mock COLA integration unavailable") from exc
        if response.is_error:
            try:
                detail = response.json().get("detail", "mock COLA request failed")
            except ValueError:
                detail = "mock COLA request failed"
            raise ColaGatewayError(response.status_code, detail)
        return response.json()

    async def search(self, clues: list[dict[str, Any]], demo_session: str) -> list[dict[str, Any]]:
        payload = await self._request(
            "POST", "/mock/v1/applications/search", demo_session,
            json={"normalization_version": "identification.v1", "clues": clues, "limit": 3},
        )
        return list(payload["candidates"])

    async def get(self, application_id: str, demo_session: str) -> dict[str, Any]:
        return await self._request("GET", f"/mock/v1/applications/{application_id}", demo_session)

    async def decide(self, application_id: str, body: dict[str, Any], demo_session: str) -> dict[str, Any]:
        return await self._request(
            "POST", f"/mock/v1/applications/{application_id}/decisions", demo_session, json=body
        )

