from flowmpeg.ui.config import UiAddress, UiLaunchOptions
from flowmpeg.ui.launcher import open_ui_browser, prepare_ui


def test_ui_launcher_binds_a_dynamic_loopback_port() -> None:
    launch = prepare_ui(UiLaunchOptions(UiAddress(port=0), open_browser=False))
    try:
        assert launch.address.host == "127.0.0.1"
        assert launch.address.port > 0
        assert launch.address.url.startswith("http://127.0.0.1:")
    finally:
        launch.close()


def test_ui_launcher_opens_the_bound_address() -> None:
    launch = prepare_ui(UiLaunchOptions(open_browser=False))
    opened: list[str] = []
    try:
        open_ui_browser(launch, opened.append)
        assert opened == [launch.address.url]
    finally:
        launch.close()
