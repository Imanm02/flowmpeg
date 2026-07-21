"""Small HTTP values shared by the local UI server."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

SECURITY_HEADERS = (
    (
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
    ),
    ("Referrer-Policy", "no-referrer"),
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
)


@dataclass(frozen=True, slots=True)
class ApiResponse:
    """A complete response returned by the UI router."""

    status: int
    body: bytes
    content_type: str
    headers: tuple[tuple[str, str], ...] = ()

    def with_security_headers(self) -> ApiResponse:
        """Return this response with browser isolation headers."""

        existing = {name.lower() for name, _ in self.headers}
        headers = (
            *self.headers,
            *(
                (name, value)
                for name, value in SECURITY_HEADERS
                if name.lower() not in existing
            ),
        )
        return ApiResponse(self.status, self.body, self.content_type, headers)


def json_response(data: Any, *, status: int = 200) -> ApiResponse:
    """Create a compact UTF-8 JSON response."""

    body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
    return ApiResponse(
        status=status,
        body=body,
        content_type="application/json; charset=utf-8",
    )


__all__ = ["ApiResponse", "SECURITY_HEADERS", "json_response"]
