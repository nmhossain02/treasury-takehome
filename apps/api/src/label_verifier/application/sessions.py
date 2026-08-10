from __future__ import annotations

import threading
import time

from label_verifier.domain.models import VerificationSession

from .errors import ApplicationError


class InMemorySessionRepository:
    """Short-lived normalized evidence only; raw image bytes never enter this repository."""

    def __init__(self) -> None:
        self._items: dict[str, VerificationSession] = {}
        self._lock = threading.RLock()

    def put(self, item: VerificationSession) -> None:
        """Store normalized verification state after purging expired sessions."""

        with self._lock:
            self._purge()
            self._items[item.verification_id] = item

    def get(self, verification_id: str, demo_session: str) -> VerificationSession:
        """Return a session only when it exists, is current, and belongs to the caller."""

        with self._lock:
            self._purge()
            item = self._items.get(verification_id)
            if item is None or item.demo_session != demo_session:
                raise ApplicationError(404, "verification not found or expired")
            return item

    def _purge(self) -> None:
        now = time.monotonic()
        for key in [key for key, item in self._items.items() if item.expires_at <= now]:
            del self._items[key]
