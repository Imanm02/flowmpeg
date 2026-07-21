import pytest

from flowmpeg.ui.request_data import MAX_JSON_BYTES, decode_json_body


def test_ui_request_decoder_reads_utf8_json() -> None:
    assert decode_json_body('{"title":"café"}'.encode()) == {"title": "café"}


def test_ui_request_decoder_rejects_oversized_bodies() -> None:
    with pytest.raises(ValueError, match="too large"):
        decode_json_body(b"x" * (MAX_JSON_BYTES + 1))


@pytest.mark.parametrize("body", [b"\xff", b"{", b'{"value":NaN}'])
def test_ui_request_decoder_rejects_invalid_json(body: bytes) -> None:
    with pytest.raises(ValueError):
        decode_json_body(body)
