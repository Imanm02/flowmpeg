from flowmpeg.ui import DEFAULT_UI_HOST, UiAddress
import pytest


def test_ui_address_defaults_to_loopback_and_dynamic_port() -> None:
    assert UiAddress() == UiAddress(host=DEFAULT_UI_HOST, port=0)


@pytest.mark.parametrize("port", [-1, 65536])
def test_ui_address_rejects_ports_outside_tcp_range(port: int) -> None:
    with pytest.raises(ValueError, match="port must be between"):
        UiAddress(port=port)


@pytest.mark.parametrize("port", [True, 3.5, "8000"])
def test_ui_address_rejects_non_integer_ports(port: object) -> None:
    with pytest.raises(TypeError, match="port must be an integer"):
        UiAddress(port=port)  # type: ignore[arg-type]
