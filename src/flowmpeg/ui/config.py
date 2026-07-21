"""Configuration values for the local Flowmpeg interface."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_UI_HOST = "127.0.0.1"


@dataclass(frozen=True, slots=True)
class UiAddress:
    """A validated local server address."""

    host: str = DEFAULT_UI_HOST
    port: int = 0
