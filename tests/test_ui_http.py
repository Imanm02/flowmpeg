import json

from flowmpeg.ui.http_types import ApiResponse, json_response


def test_ui_response_keeps_status_body_and_media_type() -> None:
    response = ApiResponse(200, b"ok", "text/plain; charset=utf-8")

    assert response.status == 200
    assert response.body == b"ok"
    assert response.content_type.startswith("text/plain")


def test_ui_json_response_uses_utf8_and_requested_status() -> None:
    response = json_response({"message": "café"}, status=201)

    assert response.status == 201
    assert response.content_type.startswith("application/json")
    assert json.loads(response.body) == {"message": "café"}


def test_ui_response_adds_security_headers_once() -> None:
    response = json_response({}).with_security_headers().with_security_headers()
    names = [name for name, _ in response.headers]

    assert names.count("Content-Security-Policy") == 1
    assert names.count("X-Content-Type-Options") == 1
