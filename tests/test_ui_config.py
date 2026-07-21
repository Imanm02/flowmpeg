from flowmpeg.ui import DEFAULT_UI_HOST, UiAddress


def test_ui_address_defaults_to_loopback_and_dynamic_port() -> None:
    assert UiAddress() == UiAddress(host=DEFAULT_UI_HOST, port=0)
