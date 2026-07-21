"""Build browser forms from Flowmpeg's terminal parser."""

from __future__ import annotations

import argparse

from flowmpeg.catalog import COMMAND_CATALOG
from flowmpeg.cli import build_parser
from flowmpeg.ui.schema import FieldKind, FieldValue, PathRole

_INPUT_FIELD_NAMES = frozenset(
    {
        "after",
        "audio_source",
        "before",
        "candidate",
        "cover_image",
        "first",
        "image",
        "inset_source",
        "music",
        "pattern",
        "reference",
        "second",
        "source",
        "sources",
        "subtitle_source",
        "video_source",
    }
)
_ADVANCED_FIELD_NAMES = frozenset(
    {
        "dry_run",
        "expected_duration",
        "explain",
        "ffmpeg",
        "ffprobe",
        "json",
        "probe_timeout",
        "progress",
        "timeout",
    }
)


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


def field_choices(action: argparse.Action) -> tuple[str, ...]:
    """Return parser choices as display-safe strings."""

    if action.choices is None:
        return ()
    return tuple(str(choice) for choice in action.choices)


def field_default(action: argparse.Action) -> FieldValue:
    """Return a default value that can be represented in JSON."""

    value = action.default
    if value is argparse.SUPPRESS or value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def field_is_multiple(action: argparse.Action) -> bool:
    """Return true when a field accepts more than one value."""

    return action.nargs in {"+", "*"} or (
        isinstance(action.nargs, int) and action.nargs > 1
    )


def field_path_role(action: argparse.Action, output_kind: str) -> PathRole:
    """Infer filesystem browsing behavior for a parser field."""

    if action.dest == "output_dir":
        return PathRole.OUTPUT_DIRECTORY
    if action.dest == "output":
        if "directory" in output_kind:
            return PathRole.OUTPUT_DIRECTORY
        return PathRole.OUTPUT_FILE
    if action.dest in _INPUT_FIELD_NAMES:
        if field_is_multiple(action):
            return PathRole.INPUT_FILES
        return PathRole.INPUT_FILE
    return PathRole.NONE


def field_is_advanced(action: argparse.Action) -> bool:
    """Return true for controls hidden behind the advanced section."""

    return action.dest in _ADVANCED_FIELD_NAMES


def command_parsers() -> dict[str, argparse.ArgumentParser]:
    """Return canonical command names mapped to their parsers."""

    parser = build_parser()
    subparsers = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    return {spec.name: subparsers.choices[spec.name] for spec in COMMAND_CATALOG}


__all__ = [
    "command_parsers",
    "field_choices",
    "field_default",
    "field_is_multiple",
    "field_is_advanced",
    "field_kind",
    "field_label",
    "field_path_role",
]
