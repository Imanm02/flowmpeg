import http.client
import json
import threading
from io import StringIO

from flowmpeg.ui.application import UiApplication
from flowmpeg.ui.config import UiAddress
from flowmpeg.ui.request_data import MAX_JSON_BYTES
from flowmpeg.ui.schema import UiSchema
from flowmpeg.ui.server import UiRequestHandler, create_server
from flowmpeg.ui.session import UiSession


def test_ui_server_serves_application_routes_on_loopback() -> None:
    application = UiApplication(UiSchema(1, (), ()), UiSession("test-token"))
    server = create_server(UiAddress(port=0), application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection(
            server.bound_address.host,
            server.bound_address.port,
            timeout=2,
        )
        connection.request("GET", "/api/health")
        response = connection.getresponse()

        assert response.status == 200
        assert response.getheader("X-Content-Type-Options") == "nosniff"
        assert b'"status":"ok"' in response.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_ui_server_passes_authorized_post_bodies_to_application() -> None:
    application = UiApplication(UiSchema(1, (), ()), UiSession("test-token"))
    server = create_server(UiAddress(port=0), application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection(
            server.bound_address.host,
            server.bound_address.port,
            timeout=2,
        )
        connection.request(
            "POST",
            "/api/preview",
            body=b"{}",
            headers={
                "Content-Type": "application/json",
                "X-Flowmpeg-Token": "test-token",
            },
        )
        response = connection.getresponse()

        assert response.status == 400
        assert json.loads(response.read())["error"] == "bad-request"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_ui_request_handler_suppresses_routine_access_logs() -> None:
    handler = object.__new__(UiRequestHandler)
    handler.log_message("%s", "request")

    assert StringIO().getvalue() == ""


def test_ui_server_rejects_oversized_body_before_reading_it() -> None:
    application = UiApplication(UiSchema(1, (), ()), UiSession("test-token"))
    server = create_server(UiAddress(port=0), application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection(
            server.bound_address.host,
            server.bound_address.port,
            timeout=2,
        )
        connection.putrequest("POST", "/api/preview")
        connection.putheader("Content-Length", str(MAX_JSON_BYTES + 1))
        connection.endheaders()
        response = connection.getresponse()

        assert response.status == 413
        assert json.loads(response.read())["error"] == "body-too-large"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
