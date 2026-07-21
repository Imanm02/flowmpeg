"""Request router for the local Flowmpeg interface."""

from __future__ import annotations

from dataclasses import dataclass

from flowmpeg import __version__
from flowmpeg.ui.http_types import ApiResponse, json_response
from flowmpeg.ui.schema import UiSchema
from flowmpeg.ui.schema_builder import build_ui_schema
from flowmpeg.ui.session import UiSession


@dataclass(frozen=True, slots=True)
class UiApplication:
    """State and routes for one local interface session."""

    schema: UiSchema
    session: UiSession

    @classmethod
    def create(cls) -> UiApplication:
        """Create an application from the installed command surface."""

        return cls(schema=build_ui_schema(), session=UiSession.create())

    def handle(self, method: str, path: str) -> ApiResponse:
        """Handle one API request."""

        if method == "GET" and path == "/api/health":
            return json_response(
                {
                    "status": "ok",
                    "version": __version__,
                    "schemaVersion": self.schema.version,
                }
            ).with_security_headers()
        return json_response(
            {"error": "not-found", "message": "Route not found"},
            status=404,
        ).with_security_headers()


__all__ = ["UiApplication"]
