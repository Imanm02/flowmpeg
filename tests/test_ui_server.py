import http.client
import json
import threading

from flowmpeg.ui.application import UiApplication
from flowmpeg.ui.config import UiAddress
from flowmpeg.ui.schema import UiSchema
from flowmpeg.ui.server import create_server
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
