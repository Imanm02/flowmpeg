"""Build browser forms from Flowmpeg's terminal parser."""

from __future__ import annotations

import argparse

from flowmpeg.catalog import COMMAND_CATALOG
from flowmpeg.cli import build_parser
from flowmpeg.ui.schema import FieldKind


def field_label(name: str) -> str:
    """Turn a parser destination into a short form label."""

    return name.replace("_", " ").capitalize()


def field_kind(action: argparse.Action) -> FieldKind:
    """Choose the browser control for one parser action."""

    if action.nargs == 0:
        return FieldKind.BOOLEAN
    if action.choices is not None:
        return FieldKind.CHOICE
    if action.type is int or action.type is float:
        return FieldKind.NUMBER
    type_name = getattr(action.type, "__name__", "")
    if type_name.endswith("_int") or type_name.endswith("_float"):
        return FieldKind.NUMBER
    return FieldKind.TEXT


def command_parsers() -> dict[str, argparse.ArgumentParser]:
    """Return canonical command names mapped to their parsers."""

    parser = build_parser()
    subparsers = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    return {spec.name: subparsers.choices[spec.name] for spec in COMMAND_CATALOG}


__all__ = ["command_parsers", "field_kind", "field_label"]
