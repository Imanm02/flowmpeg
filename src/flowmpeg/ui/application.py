"""Request router for the local Flowmpeg interface."""

from __future__ import annotations

from dataclasses import dataclass, field

from flowmpeg import __version__
from flowmpeg.ui.assets import load_asset, render_index
from flowmpeg.ui.files import list_directory
from flowmpeg.ui.http_types import ApiResponse, json_response
from flowmpeg.ui.invocation import parse_invocation
from flowmpeg.ui.jobs import JobManager
from flowmpeg.ui.preview import preview_invocation
from flowmpeg.ui.request_data import decode_json_body
from flowmpeg.ui.schema import UiSchema
from flowmpeg.ui.schema_builder import build_ui_schema
from flowmpeg.ui.serialization import directory_data, job_data, schema_data
from flowmpeg.ui.session import TOKEN_HEADER, UiSession
from flowmpeg.ui.validation import UiValidationError


@dataclass(frozen=True, slots=True)
class UiApplication:
    """State and routes for one local interface session."""

    schema: UiSchema
    session: UiSession
    jobs: JobManager = field(default_factory=JobManager, compare=False)

    @classmethod
    def create(cls) -> UiApplication:
        """Create an application from the installed command surface."""

        return cls(schema=build_ui_schema(), session=UiSession.create())

    def close(self) -> None:
        """Cancel local jobs and release worker threads."""

        self.jobs.close(wait=False)

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
        if method == "GET" and path == "/":
            asset = render_index(self.session.token)
            return ApiResponse(200, asset.data, asset.content_type).with_security_headers()
        if method == "GET" and path in {"/app.css", "/app.js"}:
            asset = load_asset(path.removeprefix("/"))
            if asset is not None:
                return ApiResponse(
                    200,
                    asset.data,
                    asset.content_type,
                    (("Cache-Control", "no-cache"),),
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
        if method == "GET" and path == "/api/jobs":
            return json_response(
                {"jobs": [job_data(job) for job in self.jobs.list()]}
            ).with_security_headers()
        if method == "GET" and path.startswith("/api/jobs/"):
            job_id = path.removeprefix("/api/jobs/")
            if "/" not in job_id:
                job = self.jobs.get(job_id)
                if job is not None:
                    return json_response(job_data(job)).with_security_headers()
                return json_response(
                    {"error": "job-not-found", "message": "Local job not found"},
                    status=404,
                ).with_security_headers()
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
        if method == "POST" and path == "/api/jobs":
            try:
                invocation = parse_invocation(decode_json_body(body))
                preview = preview_invocation(self.schema, invocation)
                job = self.jobs.start(preview.arguments, preview.display)
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
            return json_response(job_data(job), status=202).with_security_headers()
        if method == "POST" and path == "/api/jobs/clear":
            count = self.jobs.clear_finished()
            return json_response({"cleared": count}).with_security_headers()
        if method == "POST" and path == "/api/files":
            try:
                request = decode_json_body(body)
                if not isinstance(request, dict):
                    raise ValueError("file request must be an object")
                requested_path = request.get("path")
                if requested_path is not None and not isinstance(requested_path, str):
                    raise ValueError("file request path must be text or null")
                listing = list_directory(requested_path)
            except (OSError, ValueError) as error:
                return json_response(
                    {"error": "file-request", "message": str(error)},
                    status=400,
                ).with_security_headers()
            return json_response(directory_data(listing)).with_security_headers()
        if method == "POST" and path.startswith("/api/jobs/") and path.endswith(
            "/cancel"
        ):
            job_id = path.removeprefix("/api/jobs/").removesuffix("/cancel")
            if "/" in job_id or not job_id:
                return json_response(
                    {"error": "job-not-found", "message": "Local job not found"},
                    status=404,
                ).with_security_headers()
            if not self.jobs.cancel(job_id):
                status = 404 if self.jobs.get(job_id) is None else 409
                return json_response(
                    {
                        "error": "job-not-cancellable",
                        "message": "Local job is missing or already finished",
                    },
                    status=status,
                ).with_security_headers()
            job = self.jobs.get(job_id)
            if job is None:
                raise RuntimeError("cancelled job disappeared")
            return json_response(job_data(job), status=202).with_security_headers()
        return json_response(
            {"error": "not-found", "message": "Route not found"},
            status=404,
        ).with_security_headers()


__all__ = ["UiApplication"]
