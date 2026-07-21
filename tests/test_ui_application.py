import json
import threading

from flowmpeg import __version__
from flowmpeg.ui.application import UiApplication
from flowmpeg.ui.jobs import JobManager, UiJob
from flowmpeg.ui.schema import FieldKind, UiCommand, UiField, UiSchema
from flowmpeg.ui.session import UiSession


def _app() -> UiApplication:
    return UiApplication(UiSchema(1, (), ()), UiSession("test-token"))


def test_ui_health_endpoint_reports_package_and_schema_versions() -> None:
    response = _app().handle("GET", "/api/health")

    assert response.status == 200
    assert json.loads(response.body) == {
        "status": "ok",
        "version": __version__,
        "schemaVersion": 1,
    }
    assert dict(response.headers)["X-Content-Type-Options"] == "nosniff"


def test_ui_application_returns_structured_not_found_response() -> None:
    response = _app().handle("GET", "/api/missing")

    assert response.status == 404
    assert json.loads(response.body)["error"] == "not-found"


def test_ui_application_serves_shell_with_session_token() -> None:
    response = _app().handle("GET", "/")

    assert response.status == 200
    assert response.content_type.startswith("text/html")
    assert b"test-token" in response.body


def test_ui_application_serves_allow_listed_static_assets() -> None:
    response = _app().handle("GET", "/app.js")

    assert response.status == 200
    assert response.content_type.startswith("text/javascript")
    assert dict(response.headers)["Cache-Control"] == "no-cache"


def test_ui_schema_endpoint_returns_command_forms() -> None:
    command = UiCommand("errors", "help", "List errors")
    app = UiApplication(
        UiSchema(1, ("help",), (command,)),
        UiSession("test-token"),
    )

    response = app.handle("GET", "/api/schema")
    data = json.loads(response.body)

    assert response.status == 200
    assert data["commands"][0]["name"] == "errors"


def test_ui_application_rejects_post_without_session_token() -> None:
    response = _app().handle("POST", "/api/preview", body=b"{}")

    assert response.status == 403
    assert json.loads(response.body)["error"] == "invalid-token"


def test_ui_application_accepts_exact_session_token() -> None:
    response = _app().handle(
        "POST",
        "/api/missing",
        headers={"X-Flowmpeg-Token": "test-token"},
    )

    assert response.status == 404


def test_ui_preview_endpoint_returns_safe_terminal_command() -> None:
    command = UiCommand(
        "probe",
        "inspect",
        "Inspect media",
        fields=(UiField("source", "Source", FieldKind.TEXT, required=True),),
    )
    app = UiApplication(
        UiSchema(1, ("inspect",), (command,)),
        UiSession("test-token"),
    )
    response = app.handle(
        "POST",
        "/api/preview",
        headers={"X-Flowmpeg-Token": "test-token"},
        body=b'{"command":"probe","values":{"source":"input.mp4"}}',
    )

    assert response.status == 200
    assert json.loads(response.body)["display"] == "flowmpeg probe input.mp4"


def test_ui_preview_endpoint_returns_field_validation_errors() -> None:
    command = UiCommand(
        "probe",
        "inspect",
        "Inspect media",
        fields=(UiField("source", "Source", FieldKind.TEXT, required=True),),
    )
    app = UiApplication(
        UiSchema(1, ("inspect",), (command,)),
        UiSession("test-token"),
    )
    response = app.handle(
        "POST",
        "/api/preview",
        headers={"X-Flowmpeg-Token": "test-token"},
        body=b'{"command":"probe","values":{}}',
    )

    data = json.loads(response.body)
    assert response.status == 422
    assert data["issues"][0]["field"] == "source"


def test_ui_preview_endpoint_rejects_invalid_json() -> None:
    response = _app().handle(
        "POST",
        "/api/preview",
        headers={"X-Flowmpeg-Token": "test-token"},
        body=b"{",
    )

    assert response.status == 400
    assert json.loads(response.body)["error"] == "bad-request"


def test_ui_application_owns_a_local_job_manager() -> None:
    application = _app()
    try:
        queued = application.jobs.start(("errors",), "flowmpeg errors")
        finished = application.jobs.wait(queued.id, timeout=10)

        assert finished.returncode == 0
    finally:
        application.close()


def test_ui_job_endpoint_starts_a_validated_local_command() -> None:
    command = UiCommand("errors", "help", "List errors")
    application = UiApplication(
        UiSchema(1, ("help",), (command,)),
        UiSession("test-token"),
    )
    try:
        response = application.handle(
            "POST",
            "/api/jobs",
            headers={"X-Flowmpeg-Token": "test-token"},
            body=b'{"command":"errors","values":{}}',
        )
        queued = json.loads(response.body)
        finished = application.jobs.wait(queued["id"], timeout=10)

        assert response.status == 202
        assert finished.returncode == 0
        assert "FMG200" in finished.output
    finally:
        application.close()


def test_ui_job_endpoint_rejects_nested_ui_command() -> None:
    command = UiCommand("ui", "help", "Open local application")
    application = UiApplication(
        UiSchema(1, ("help",), (command,)),
        UiSession("test-token"),
    )
    try:
        response = application.handle(
            "POST",
            "/api/jobs",
            headers={"X-Flowmpeg-Token": "test-token"},
            body=b'{"command":"ui","values":{}}',
        )

        assert response.status == 400
        assert "cannot be started" in json.loads(response.body)["message"]
    finally:
        application.close()


def test_ui_job_read_endpoints_return_session_jobs() -> None:
    application = _app()
    try:
        queued = application.jobs.start(("errors",), "flowmpeg errors")
        application.jobs.wait(queued.id, timeout=10)

        listing = application.handle("GET", "/api/jobs")
        detail = application.handle("GET", f"/api/jobs/{queued.id}")

        assert json.loads(listing.body)["jobs"][0]["id"] == queued.id
        assert json.loads(detail.body)["id"] == queued.id
    finally:
        application.close()


def test_ui_job_detail_returns_structured_not_found() -> None:
    application = _app()
    try:
        response = application.handle("GET", "/api/jobs/missing")

        assert response.status == 404
        assert json.loads(response.body)["error"] == "job-not-found"
    finally:
        application.close()


def test_ui_job_cancel_and_clear_endpoints_manage_session_jobs() -> None:
    release = threading.Event()

    def wait_for_release(job: UiJob) -> int:
        del job
        release.wait(timeout=2)
        return 130

    manager = JobManager(runner=wait_for_release)
    application = UiApplication(
        UiSchema(1, (), ()),
        UiSession("test-token"),
        manager,
    )
    try:
        queued = manager.start(("errors",), "flowmpeg errors")
        response = application.handle(
            "POST",
            f"/api/jobs/{queued.id}/cancel",
            headers={"X-Flowmpeg-Token": "test-token"},
        )
        release.set()
        manager.wait(queued.id, timeout=2)
        cleared = application.handle(
            "POST",
            "/api/jobs/clear",
            headers={"X-Flowmpeg-Token": "test-token"},
        )

        assert response.status == 202
        assert json.loads(cleared.body) == {"cleared": 1}
    finally:
        release.set()
        application.close()
