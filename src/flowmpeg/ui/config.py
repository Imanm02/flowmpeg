"""Configuration values for the local Flowmpeg interface."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_UI_HOST = "127.0.0.1"


@dataclass(frozen=True, slots=True)
class UiAddress:
    """A validated local server address."""

    host: str = DEFAULT_UI_HOST
    port: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.port, bool) or not isinstance(self.port, int):
            raise TypeError("port must be an integer")
        if not 0 <= self.port <= 65535:
            raise ValueError("port must be between 0 and 65535")
