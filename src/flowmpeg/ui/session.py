"""Per-launch request authorization for the local UI."""

from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass

TOKEN_HEADER = "X-Flowmpeg-Token"


@dataclass(frozen=True, slots=True)
class UiSession:
    """A random token accepted by one running UI server."""

    token: str

    @classmethod
    def create(cls) -> UiSession:
        """Create a token with enough entropy for a local session."""

        return cls(secrets.token_urlsafe(32))

    def accepts(self, candidate: str | None) -> bool:
        """Check a request token without timing-sensitive equality."""

        return candidate is not None and hmac.compare_digest(self.token, candidate)


__all__ = ["TOKEN_HEADER", "UiSession"]
