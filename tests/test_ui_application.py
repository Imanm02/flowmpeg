import json

from flowmpeg import __version__
from flowmpeg.ui.application import UiApplication
from flowmpeg.ui.schema import UiSchema
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
