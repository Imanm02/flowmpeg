"""Decode bounded requests received by the local UI server."""

from __future__ import annotations

import json
from typing import Any

MAX_JSON_BYTES = 1_048_576


def decode_json_body(body: bytes) -> Any:
    """Decode one bounded UTF-8 JSON body."""

    if len(body) > MAX_JSON_BYTES:
        raise ValueError("request body is too large")
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("request body must be UTF-8") from error
    try:
        return json.loads(
            text,
            parse_constant=lambda value: _reject_constant(value),
        )
    except json.JSONDecodeError as error:
        raise ValueError("request body must contain valid JSON") from error


def _reject_constant(value: str) -> None:
    raise ValueError(f"nonfinite JSON number is not allowed: {value}")


__all__ = ["MAX_JSON_BYTES", "decode_json_body"]
