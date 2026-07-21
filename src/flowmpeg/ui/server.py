"""Loopback HTTP server for the local Flowmpeg interface."""

from __future__ import annotations

import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import cast
from urllib.parse import urlsplit

from flowmpeg.ui.application import UiApplication
from flowmpeg.ui.config import UiAddress
from flowmpeg.ui.http_types import ApiResponse, json_response
from flowmpeg.ui.request_data import MAX_JSON_BYTES


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

    def log_message(self, format: str, *args: object) -> None:
        """Keep routine browser polling out of the terminal."""

        del format, args

    def do_GET(self) -> None:
        """Serve an application GET route."""

        self._send(self._application.handle("GET", urlsplit(self.path).path))

    def do_POST(self) -> None:
        """Serve an application POST route with a bounded body."""

        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length or "0")
        except ValueError:
            self._send(
                json_response(
                    {"error": "bad-length", "message": "Invalid Content-Length"},
                    status=400,
                ).with_security_headers()
            )
            return
        if length < 0 or length > MAX_JSON_BYTES:
            self._send(
                json_response(
                    {"error": "body-too-large", "message": "Request body is too large"},
                    status=413,
                ).with_security_headers()
            )
            return
        body = self.rfile.read(length)
        headers = {name: value for name, value in self.headers.items()}
        response = self._application.handle(
            "POST",
            urlsplit(self.path).path,
            headers=headers,
            body=body,
        )
        self._send(response)

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
    """Bind a local UI server without starting its request loop."""

    server_type = UiHttpServerV6 if address.host == "::1" else UiHttpServer
    return server_type(address, application)


__all__ = ["UiHttpServer", "UiRequestHandler", "create_server"]
