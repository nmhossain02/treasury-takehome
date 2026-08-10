from __future__ import annotations


class ApplicationError(Exception):
    """An expected workflow failure that can be presented to an API client."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
