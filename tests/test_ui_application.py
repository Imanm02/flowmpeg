import json

from flowmpeg import __version__
from flowmpeg.ui.application import UiApplication
from flowmpeg.ui.schema import UiCommand, UiSchema
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
