from flowmpeg.ui.http_types import ApiResponse


def test_ui_response_keeps_status_body_and_media_type() -> None:
    response = ApiResponse(200, b"ok", "text/plain; charset=utf-8")

    assert response.status == 200
    assert response.body == b"ok"
    assert response.content_type.startswith("text/plain")
