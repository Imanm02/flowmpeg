"""Packaged browser files for the local interface."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files

_CONTENT_TYPES = {
    "app.css": "text/css; charset=utf-8",
    "app.js": "text/javascript; charset=utf-8",
    "index.html": "text/html; charset=utf-8",
}


@dataclass(frozen=True, slots=True)
class StaticAsset:
    """One known packaged browser file."""

    name: str
    data: bytes
    content_type: str


def load_asset(name: str) -> StaticAsset | None:
    """Load an allow-listed packaged asset."""

    content_type = _CONTENT_TYPES.get(name)
    if content_type is None:
        return None
    resource = files("flowmpeg.ui").joinpath("static", name)
    return StaticAsset(name, resource.read_bytes(), content_type)


__all__ = ["StaticAsset", "load_asset"]
