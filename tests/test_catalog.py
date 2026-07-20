import argparse
from typing import cast

from flowmpeg.catalog import CATEGORIES, COMMAND_CATALOG, TAGS, command_spec
from flowmpeg.cli import build_parser


def test_catalog_matches_every_cli_command_and_alias() -> None:
    parser = build_parser()
    command_action = next(
        action for action in parser._actions if action.dest == "command"
    )
    choices = cast(dict[str, argparse.ArgumentParser], command_action.choices)
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
    assert all(spec.tags for spec in COMMAND_CATALOG)
    assert all(set(spec.tags) <= set(TAGS) for spec in COMMAND_CATALOG)
    assert command_spec("gif") == command_spec("make-gif")


def test_editing_commands_list_exact_requirements() -> None:
    editing = [
        spec for spec in COMMAND_CATALOG if spec.category not in {"help", "inspect"}
    ]

    assert editing
    assert all(spec.requirements for spec in editing)
    assert command_spec("trim").requirements == (
        "encoder:aac",
        "encoder:libx264",
        "filter:asetpts",
        "filter:atrim",
        "filter:setpts",
        "filter:trim",
        "muxer:mp4",
    )
