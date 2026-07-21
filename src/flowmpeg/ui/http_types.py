"""Small HTTP values shared by the local UI server."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ApiResponse:
    """A complete response returned by the UI router."""

    status: int
    body: bytes
    content_type: str
    headers: tuple[tuple[str, str], ...] = ()


def json_response(data: Any, *, status: int = 200) -> ApiResponse:
    """Create a compact UTF-8 JSON response."""

    body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
    return ApiResponse(
        status=status,
        body=body,
        content_type="application/json; charset=utf-8",
    )


__all__ = ["ApiResponse", "json_response"]
