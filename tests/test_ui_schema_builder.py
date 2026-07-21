import argparse

from flowmpeg.catalog import COMMAND_CATALOG
from flowmpeg.ui.schema import FieldKind
from flowmpeg.ui.schema_builder import command_parsers, field_kind, field_label


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
