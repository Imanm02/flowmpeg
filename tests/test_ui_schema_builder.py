from flowmpeg.catalog import COMMAND_CATALOG
from flowmpeg.ui.schema_builder import command_parsers, field_label


def test_ui_maps_every_canonical_command_parser() -> None:
    parsers = command_parsers()

    assert tuple(parsers) == tuple(spec.name for spec in COMMAND_CATALOG)
    assert all(parser.prog.startswith("flowmpeg ") for parser in parsers.values())


def test_ui_field_labels_replace_parser_underscores() -> None:
    assert field_label("expected_duration") == "Expected duration"
