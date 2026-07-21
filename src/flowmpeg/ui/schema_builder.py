"""Build browser forms from Flowmpeg's terminal parser."""

from __future__ import annotations

import argparse

from flowmpeg.catalog import COMMAND_CATALOG
from flowmpeg.cli import build_parser


def field_label(name: str) -> str:
    """Turn a parser destination into a short form label."""

    return name.replace("_", " ").capitalize()


def command_parsers() -> dict[str, argparse.ArgumentParser]:
    """Return canonical command names mapped to their parsers."""

    parser = build_parser()
    subparsers = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    return {spec.name: subparsers.choices[spec.name] for spec in COMMAND_CATALOG}


__all__ = ["command_parsers", "field_label"]
