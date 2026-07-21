"""Loopback HTTP server for the local Flowmpeg interface."""

from __future__ import annotations

import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import cast
from urllib.parse import urlsplit

from flowmpeg.ui.application import UiApplication
from flowmpeg.ui.config import UiAddress
from flowmpeg.ui.http_types import ApiResponse


class UiHttpServer(ThreadingHTTPServer):
    """A threaded loopback server carrying one UI application."""

    daemon_threads = True

    def __init__(self, address: UiAddress, application: UiApplication) -> None:
        self.application = application
        super().__init__((address.host, address.port), UiRequestHandler)

    @property
    def bound_address(self) -> UiAddress:
        """Return the address selected by the operating system."""

        host, port = self.server_address[:2]
        return UiAddress(str(host), int(port))


class UiHttpServerV6(UiHttpServer):
    """IPv6 form of the local UI server."""

    address_family = socket.AF_INET6


class UiRequestHandler(BaseHTTPRequestHandler):
    """Translate HTTP requests into application router calls."""

    server_version = "FlowmpegUI"

    def do_GET(self) -> None:
        """Serve an application GET route.""

        self._send(self._application.handle("GET", urlsplit(self.path).path))

    def _send(self, response: ApiResponse) -> None:
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        for name, value in response.headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(response.body)

    @property
    def _application(self) -> UiApplication:
        return cast(UiHttpServer, self.server).application


def create_server(address: UiAddress, application: UiApplication) -> UiHttpServer:
    """Bind a local UI server without starting its request loop.""

    server_type = UiHttpServerV6 if address.host == "::1" else UiHttpServer
    return server_type(address, application)


__all__ = ["UiHttpServer", "UiRequestHandler", "create_server"]
