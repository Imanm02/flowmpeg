"""Build browser forms from Flowmpeg's terminal parser."""

from __future__ import annotations

import argparse

from flowmpeg.catalog import CATEGORIES, COMMAND_CATALOG, CommandSpec
from flowmpeg.cli import build_parser
from flowmpeg.ui.schema import (
    FieldKind,
    FieldValue,
    PathRole,
    UiCommand,
    UiField,
    UiSchema,
)

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


def field_help(action: argparse.Action) -> str:
    """Return useful parser help without argparse placeholders."""

    if action.help is None or action.help is argparse.SUPPRESS:
        return ""
    return str(action.help).replace("%(default)s", str(field_default(action)))


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


def build_ui_field(action: argparse.Action, output_kind: str) -> UiField:
    """Build one typed form field from an argparse action."""

    flags = tuple(
        flag for flag in action.option_strings if not flag.startswith("--no-")
    )
    negative_flags = tuple(
        flag for flag in action.option_strings if flag.startswith("--no-")
    )
    if isinstance(action, argparse._StoreFalseAction):
        flags = ()
        negative_flags = tuple(action.option_strings)
    clear_flags: tuple[str, ...] = ()
    if isinstance(action, argparse._StoreConstAction) and action.const is None:
        flags = ()
        clear_flags = tuple(action.option_strings)
    return UiField(
        name=action.dest,
        label=field_label(action.dest),
        kind=field_kind(action),
        flags=flags,
        negative_flags=negative_flags,
        clear_flags=clear_flags,
        required=action.required,
        multiple=field_is_multiple(action),
        default=field_default(action),
        help=field_help(action),
        choices=field_choices(action),
        path_role=field_path_role(action, output_kind),
        advanced=field_is_advanced(action),
    )


def merge_ui_fields(fields: tuple[UiField, ...]) -> tuple[UiField, ...]:
    """Merge parser actions that write to the same destination."""

    merged: dict[str, UiField] = {}
    for field in fields:
        current = merged.get(field.name)
        if current is None:
            merged[field.name] = field
            continue
        merged[field.name] = UiField(
            name=current.name,
            label=current.label,
            kind=current.kind,
            flags=(*current.flags, *field.flags),
            negative_flags=(*current.negative_flags, *field.negative_flags),
            clear_flags=(*current.clear_flags, *field.clear_flags),
            required=current.required or field.required,
            multiple=current.multiple or field.multiple,
            default=current.default,
            help=current.help or field.help,
            choices=current.choices or field.choices,
            path_role=current.path_role,
            advanced=current.advanced and field.advanced,
        )
    return tuple(merged.values())


def form_actions(parser: argparse.ArgumentParser) -> tuple[argparse.Action, ...]:
    """Return actions that should appear in a command form."""

    return tuple(
        action
        for action in parser._actions
        if not isinstance(action, argparse._HelpAction)
    )


def build_ui_command(
    spec: CommandSpec,
    parser: argparse.ArgumentParser,
) -> UiCommand:
    """Build one browser command from catalog and parser metadata."""

    fields = merge_ui_fields(
        tuple(
            build_ui_field(action, spec.output_kind) for action in form_actions(parser)
        )
    )
    return UiCommand(
        name=spec.name,
        category=spec.category,
        summary=spec.summary,
        aliases=spec.aliases,
        tags=spec.tags,
        input_kind=spec.input_kind,
        output_kind=spec.output_kind,
        fields=fields,
    )


def command_parsers() -> dict[str, argparse.ArgumentParser]:
    """Return canonical command names mapped to their parsers."""

    parser = build_parser()
    subparsers = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    return {spec.name: subparsers.choices[spec.name] for spec in COMMAND_CATALOG}


def build_ui_schema() -> UiSchema:
    """Build the complete browser schema from current command metadata."""

    parsers = command_parsers()
    commands = tuple(
        build_ui_command(spec, parsers[spec.name]) for spec in COMMAND_CATALOG
    )
    return UiSchema(version=1, categories=CATEGORIES, commands=commands)


__all__ = [
    "build_ui_schema",
    "build_ui_field",
    "build_ui_command",
    "command_parsers",
    "field_choices",
    "field_default",
    "field_help",
    "field_is_multiple",
    "field_is_advanced",
    "field_kind",
    "field_label",
    "field_path_role",
    "form_actions",
    "merge_ui_fields",
]
