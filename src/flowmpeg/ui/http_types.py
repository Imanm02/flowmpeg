"""Small HTTP values shared by the local UI server."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApiResponse:
    """A complete response returned by the UI router."""

    status: int
    body: bytes
    content_type: str
    headers: tuple[tuple[str, str], ...] = ()


__all__ = ["ApiResponse"]
