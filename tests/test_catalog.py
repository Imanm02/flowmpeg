from flowmpeg.catalog import CATEGORIES, COMMAND_CATALOG, command_spec
from flowmpeg.cli import build_parser


def test_catalog_matches_every_cli_command_and_alias() -> None:
    parser = build_parser()
    command_action = next(
        action for action in parser._actions if action.dest == "command"
    )
    choices = command_action.choices
    assert choices is not None

    catalog_names = {spec.name for spec in COMMAND_CATALOG}
    canonical_names: set[str] = set()
    seen_parsers: set[int] = set()
    for name, command_parser in choices.items():
        if id(command_parser) in seen_parsers:
            continue
        seen_parsers.add(id(command_parser))
        canonical_names.add(name)
        aliases = {
            alias
            for alias, alias_parser in choices.items()
            if alias_parser is command_parser and alias != name
        }
        spec = command_spec(name)
        assert spec is not None
        assert set(spec.aliases) == aliases

    assert catalog_names == canonical_names


def test_catalog_fields_support_task_discovery() -> None:
    assert len(COMMAND_CATALOG) == len({spec.name for spec in COMMAND_CATALOG})
    assert set(CATEGORIES) == {spec.category for spec in COMMAND_CATALOG}
    assert all(spec.summary for spec in COMMAND_CATALOG)
    assert command_spec("gif") == command_spec("make-gif")
