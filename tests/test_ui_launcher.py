from io import StringIO

import pytest

from flowmpeg.ui.config import UiAddress, UiLaunchOptions
from flowmpeg.ui.launcher import open_ui_browser, prepare_ui, serve_ui
from flowmpeg.ui.server import UiHttpServer


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


def test_ui_server_cleanup_runs_after_request_loop_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = StringIO()
    closed: list[bool] = []

    def fail(self: UiHttpServer) -> None:
        raise RuntimeError("stop test server")

    def record_close(self: UiHttpServer) -> None:
        closed.append(True)
        super(UiHttpServer, self).server_close()

    monkeypatch.setattr(UiHttpServer, "serve_forever", fail)
    monkeypatch.setattr(UiHttpServer, "server_close", record_close)

    with pytest.raises(RuntimeError, match="stop test server"):
        serve_ui(UiLaunchOptions(open_browser=False), output)

    assert closed == [True]
    assert output.getvalue().startswith("Flowmpeg UI: http://127.0.0.1:")
