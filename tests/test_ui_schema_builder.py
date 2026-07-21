import argparse

from flowmpeg.catalog import COMMAND_CATALOG, command_spec
from flowmpeg.ui.schema import FieldKind, PathRole, UiField
from flowmpeg.ui.schema_builder import (
    build_ui_command,
    build_ui_field,
    build_ui_schema,
    command_examples,
    command_parsers,
    field_choices,
    field_default,
    field_help,
    field_is_advanced,
    field_is_integer,
    field_is_multiple,
    field_kind,
    field_label,
    field_minimum,
    field_path_role,
    form_actions,
    merge_ui_fields,
)


def test_ui_maps_every_canonical_command_parser() -> None:
    parsers = command_parsers()

    assert tuple(parsers) == tuple(spec.name for spec in COMMAND_CATALOG)
    assert all(parser.prog.startswith("flowmpeg ") for parser in parsers.values())


def test_ui_field_labels_replace_parser_underscores() -> None:
    assert field_label("expected_duration") == "Expected duration"


def test_ui_field_kind_recognizes_flags_choices_and_numbers() -> None:
    parser = argparse.ArgumentParser()
    enabled = parser.add_argument("--enabled", action="store_true")
    codec = parser.add_argument("--codec", choices=("aac", "mp3"))
    count = parser.add_argument("--count", type=int)
    source = parser.add_argument("source")

    assert field_kind(enabled) is FieldKind.BOOLEAN
    assert field_kind(codec) is FieldKind.CHOICE
    assert field_kind(count) is FieldKind.NUMBER
    assert field_kind(source) is FieldKind.TEXT
    assert field_is_integer(count) is True
    assert field_is_integer(source) is False


def test_ui_field_choices_convert_numeric_values_to_text() -> None:
    parser = argparse.ArgumentParser()
    action = parser.add_argument("--level", choices=(1, 2, 3))

    assert field_choices(action) == ("1", "2", "3")


def test_ui_field_default_hides_suppressed_values() -> None:
    parser = argparse.ArgumentParser()
    hidden = parser.add_argument("--hidden", default=argparse.SUPPRESS)
    timeout = parser.add_argument("--timeout", type=float, default=10.0)

    assert field_default(hidden) is None
    assert field_default(timeout) == 10.0


def test_ui_infers_positive_and_nonnegative_bounds() -> None:
    parser = command_parsers()["trim"]
    actions = {action.dest: action for action in form_actions(parser)}

    assert field_minimum(actions["duration"]) == (0, True)
    assert field_minimum(actions["start"]) == (0, False)


def test_ui_detects_repeatable_and_fixed_group_fields() -> None:
    parser = argparse.ArgumentParser()
    sources = parser.add_argument("sources", nargs="+")
    pair = parser.add_argument("--pair", nargs=2)
    source = parser.add_argument("source")

    assert field_is_multiple(sources) is True
    assert field_is_multiple(pair) is True
    assert field_is_multiple(source) is False


def test_ui_infers_input_and_output_path_roles() -> None:
    parser = argparse.ArgumentParser()
    source = parser.add_argument("source")
    sources = parser.add_argument("sources", nargs="+")
    output = parser.add_argument("-o", "--output")

    assert field_path_role(source, "media") is PathRole.INPUT_FILE
    assert field_path_role(sources, "media") is PathRole.INPUT_FILES
    assert field_path_role(output, "media") is PathRole.OUTPUT_FILE
    assert field_path_role(output, "artifact directory") is PathRole.OUTPUT_DIRECTORY


def test_ui_groups_runtime_controls_as_advanced() -> None:
    parser = argparse.ArgumentParser()
    ffmpeg = parser.add_argument("--ffmpeg")
    timeout = parser.add_argument("--timeout")
    overwrite = parser.add_argument("--overwrite", action="store_true")

    assert field_is_advanced(ffmpeg) is True
    assert field_is_advanced(timeout) is True
    assert field_is_advanced(overwrite) is False


def test_ui_normalizes_action_help_and_default_placeholders() -> None:
    parser = argparse.ArgumentParser()
    timeout = parser.add_argument(
        "--timeout",
        default=10,
        help="Stop after %(default)s seconds",
    )
    unnamed = parser.add_argument("--unnamed")

    assert field_help(timeout) == "Stop after 10 seconds"
    assert field_help(unnamed) == ""


def test_ui_builds_a_complete_field_from_an_action() -> None:
    parser = argparse.ArgumentParser()
    action = parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output path",
    )

    field = build_ui_field(action, "media")

    assert field.name == "output"
    assert field.flags == ("-o", "--output")
    assert field.required is True
    assert field.help == "Output path"
    assert field.path_role is PathRole.OUTPUT_FILE


def test_ui_merges_negative_and_clear_actions_by_destination() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", dest="duration", type=float, default=5.0)
    parser.add_argument("--full", dest="duration", action="store_const", const=None)
    fields = tuple(build_ui_field(action, "media") for action in form_actions(parser))

    assert merge_ui_fields(fields) == (
        UiField(
            name="duration",
            label="Duration",
            kind=FieldKind.NUMBER,
            flags=("--duration",),
            clear_flags=("--full",),
            default=5.0,
        ),
    )


def test_ui_form_actions_hide_argparse_help() -> None:
    parser = argparse.ArgumentParser()
    source = parser.add_argument("source")

    assert form_actions(parser) == (source,)


def test_ui_builds_commands_from_catalog_and_parser_metadata() -> None:
    spec = command_spec("trim")
    assert spec is not None
    command = build_ui_command(spec, command_parsers()["trim"])

    assert command.name == "trim"
    assert command.category == "video"
    assert command.aliases == ("cut",)
    assert {field.name for field in command.fields} >= {
        "source",
        "start",
        "duration",
        "output",
    }
    assert "flowmpeg cut input.mp4 --start 5 --duration 12 -o clip.mp4" in (
        command.examples
    )


def test_ui_command_examples_resolve_aliases() -> None:
    examples = command_examples()

    assert "flowmpeg cut input.mp4 --start 5 --duration 12 -o clip.mp4" in (
        examples["trim"]
    )
    assert "flowmpeg audio input.mp4 -o track.mp3" in examples["extract-audio"]


def test_ui_schema_covers_every_catalog_command() -> None:
    schema = build_ui_schema()

    assert tuple(command.name for command in schema.commands) == tuple(
        spec.name for spec in COMMAND_CATALOG
    )
    assert [command.name for command in schema.commands if not command.fields] == [
        "errors"
    ]
