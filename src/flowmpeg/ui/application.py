"""Request router for the local Flowmpeg interface."""

from __future__ import annotations

from dataclasses import dataclass

from flowmpeg import __version__
from flowmpeg.ui.http_types import ApiResponse, json_response
from flowmpeg.ui.invocation import parse_invocation
from flowmpeg.ui.preview import preview_invocation
from flowmpeg.ui.request_data import decode_json_body
from flowmpeg.ui.schema import UiSchema
from flowmpeg.ui.schema_builder import build_ui_schema
from flowmpeg.ui.serialization import schema_data
from flowmpeg.ui.session import TOKEN_HEADER, UiSession
from flowmpeg.ui.validation import UiValidationError


@dataclass(frozen=True, slots=True)
class UiApplication:
    """State and routes for one local interface session."""

    schema: UiSchema
    session: UiSession

    @classmethod
    def create(cls) -> UiApplication:
        """Create an application from the installed command surface."""

        return cls(schema=build_ui_schema(), session=UiSession.create())

    def handle(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes = b"",
    ) -> ApiResponse:
        """Handle one API request."""

        request_headers = {name.lower(): value for name, value in (headers or {}).items()}
        if method in {"POST", "PUT", "PATCH", "DELETE"} and not self.session.accepts(
            request_headers.get(TOKEN_HEADER.lower())
        ):
            return json_response(
                {
                    "error": "invalid-token",
                    "message": "The local UI request token is missing or invalid",
                },
                status=403,
            ).with_security_headers()
        if method == "GET" and path == "/api/health":
            return json_response(
                {
                    "status": "ok",
                    "version": __version__,
                    "schemaVersion": self.schema.version,
                }
            ).with_security_headers()
        if method == "GET" and path == "/api/schema":
            return json_response(schema_data(self.schema)).with_security_headers()
        if method == "POST" and path == "/api/preview":
            try:
                invocation = parse_invocation(decode_json_body(body))
                preview = preview_invocation(self.schema, invocation)
            except UiValidationError as error:
                return json_response(
                    {
                        "error": "validation",
                        "issues": [
                            {
                                "code": issue.code,
                                "message": issue.message,
                                "field": issue.field,
                            }
                            for issue in error.issues
                        ],
                    },
                    status=422,
                ).with_security_headers()
            except ValueError as error:
                return json_response(
                    {"error": "bad-request", "message": str(error)},
                    status=400,
                ).with_security_headers()
            return json_response(
                {
                    "arguments": list(preview.arguments),
                    "display": preview.display,
                }
            ).with_security_headers()
        return json_response(
            {"error": "not-found", "message": "Route not found"},
            status=404,
        ).with_security_headers()


__all__ = ["UiApplication"]
