"""Start and stop the local Flowmpeg interface."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TextIO
import webbrowser

from flowmpeg.ui.application import UiApplication
from flowmpeg.ui.config import UiAddress, UiLaunchOptions
from flowmpeg.ui.server import UiHttpServer, create_server


@dataclass(slots=True)
class UiLaunch:
    """A bound server ready to enter its request loop."""

    server: UiHttpServer
    address: UiAddress

    def close(self) -> None:
        """Release the bound local port."""

        self.server.server_close()


def prepare_ui(options: UiLaunchOptions) -> UiLaunch:
    """Build the application and bind its loopback server."""

    server = create_server(options.address, UiApplication.create())
    return UiLaunch(server=server, address=server.bound_address)


def open_ui_browser(
    launch: UiLaunch,
    opener: Callable[[str], object] = webbrowser.open,
) -> None:
    """Open the exact bound address with the platform browser."""

    opener(launch.address.url)


def serve_ui(
    options: UiLaunchOptions,
    output: TextIO,
    *,
    opener: Callable[[str], object] = webbrowser.open,
) -> None:
    """Run the UI until interrupted and always release its port."""

    launch = prepare_ui(options)
    try:
        print(f"Flowmpeg UI: {launch.address.url}", file=output, flush=True)
        if options.open_browser:
            open_ui_browser(launch, opener)
        launch.server.serve_forever()
    finally:
        launch.close()


__all__ = ["UiLaunch", "open_ui_browser", "prepare_ui", "serve_ui"]
