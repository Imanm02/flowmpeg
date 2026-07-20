"""Safe display helpers for commands and errors."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from collections.abc import Iterable

_url_user_info = re.compile(r"(?i)([a-z][a-z0-9+.-]*://)([^/@\s]+@)")
_header_secret = re.compile(
    r"(?im)^(authorization|cookie|proxy-authorization|x-api-key)(\s*:\s*).+$"
)
_query_secret = re.compile(
    r"(?i)([?&](?:access_?token|api_?key|googleaccessid|key|key-pair-id|"
    r"policy|sig|signature|token|x-amz-credential|x-amz-security-token|"
    r"x-amz-signature|x-goog-signature)=)([^&#\s\"']+)"
)
_secret_options = {
    "-authorization",
    "-cookie",
    "-cookies",
    "-headers",
    "-http_proxy",
}
_cmd_metacharacters = frozenset("&|<>()^")


def redact_argv(argv: Iterable[str]) -> tuple[str, ...]:
    """Return command tokens with common credential locations hidden."""

    redacted: list[str] = []
    hide_next = False

    for token in argv:
        if hide_next:
            redacted.append("<redacted>")
            hide_next = False
            continue

        redacted.append(_redact_token(token))
        if token.lower() in _secret_options:
            hide_next = True

    return tuple(redacted)


def redact_text(text: str) -> str:
    """Hide URL user information and common secret headers in text."""

    return _redact_token(text)


def display_argv(argv: Iterable[str], *, redact: bool = True) -> str:
    """Format command tokens for the current platform."""

    values = tuple(argv)
    if redact:
        values = redact_argv(values)
    if os.name == "nt":
        return _windows_display_argv(values)
    return shlex.join(values)


def _windows_display_argv(argv: Iterable[str]) -> str:
    tokens: list[str] = []
    for value in argv:
        rendered = subprocess.list2cmdline((value,))
        if any(character in value for character in _cmd_metacharacters) and not (
            rendered.startswith('"') and rendered.endswith('"')
        ):
            rendered = f'"{rendered}"'
        tokens.append(rendered)
    return " ".join(tokens)


def _redact_token(token: str) -> str:
    token = _url_user_info.sub(r"\1<redacted>@", token)
    token = _query_secret.sub(r"\1<redacted>", token)
    return _header_secret.sub(r"\1\2<redacted>", token)
