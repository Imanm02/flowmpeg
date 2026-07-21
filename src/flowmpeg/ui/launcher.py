"""Start and stop the local Flowmpeg interface."""

from __future__ import annotations

from dataclasses import dataclass

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


__all__ = ["UiLaunch", "prepare_ui"]
