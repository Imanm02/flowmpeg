import pytest

from flowmpeg.ui import DEFAULT_UI_HOST, UiAddress, UiLaunchOptions


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


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.4", "example.com"])
def test_ui_address_rejects_non_loopback_hosts(host: str) -> None:
    with pytest.raises(ValueError, match="loopback"):
        UiAddress(host=host)


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "LOCALHOST"])
def test_ui_address_accepts_loopback_names(host: str) -> None:
    assert UiAddress(host=host).host == host


def test_ui_address_builds_browser_url() -> None:
    assert UiAddress(port=8123).url == "http://127.0.0.1:8123/"


def test_ui_address_brackets_ipv6_in_browser_url() -> None:
    assert UiAddress(host="::1", port=8123).url == "http://[::1]:8123/"


def test_ui_launch_options_open_browser_by_default() -> None:
    options = UiLaunchOptions()

    assert options.address == UiAddress()
    assert options.open_browser is True
