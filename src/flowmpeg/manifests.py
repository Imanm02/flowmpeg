"""Load bounded JSON batches through the existing media command parser."""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path

from flowmpeg.batch import BatchJob
from flowmpeg.catalog import MANIFEST_COMMANDS, command_spec
from flowmpeg.errors import GraphError

MAX_MANIFEST_BYTES = 1_048_576
MAX_MANIFEST_JOBS = 1_000
_EXECUTION_FLAGS = frozenset(
    {
        "-h",
        "--help",
        "--version",
        "--ffmpeg",
        "--ffprobe",
        "--probe-timeout",
        "--dry-run",
        "--explain",
        "--progress",
        "--no-progress",
        "--overwrite",
        "--timeout",
        "--expected-duration",
    }
)


def load_batch_manifest(path: str | os.PathLike[str]) -> tuple[BatchJob, ...]:
    """Validate a version-one manifest and build plans without starting tools."""

    source = Path(path).resolve()
    try:
        with source.open("rb") as stream:
            raw = stream.read(MAX_MANIFEST_BYTES + 1)
        if len(raw) > MAX_MANIFEST_BYTES:
            raise GraphError("Batch manifests cannot exceed 1 MiB")
        data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_keys)
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        raise GraphError("Batch manifest could not be read as valid JSON") from error
    if not isinstance(data, dict) or set(data) != {"schema_version", "jobs"}:
        raise GraphError("Batch manifests require only schema_version and jobs")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise GraphError("Batch manifest schema_version must be 1")
    entries = data["jobs"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_MANIFEST_JOBS:
        raise GraphError("Batch manifests require between 1 and 1000 jobs")
    jobs = tuple(_build_job(entry, source.parent) for entry in entries)
    if len({job.name for job in jobs}) != len(jobs):
        raise GraphError("Batch manifest job names must be unique")
    return jobs


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise GraphError("Batch manifest objects cannot repeat keys")
        result[key] = value
    return result


def _build_job(entry: object, root: Path) -> BatchJob:
    from flowmpeg.cli import _build_media_plan, build_parser

    if not isinstance(entry, dict) or set(entry) - {"name", "command", "timeout"}:
        raise GraphError("Batch jobs accept only name, command, and timeout")
    name = entry.get("name")
    arguments = entry.get("command")
    if not isinstance(name, str) or not name.strip() or len(name) > 200:
        raise GraphError("Batch job names require 1 to 200 characters")
    if (
        not isinstance(arguments, list)
        or not 1 <= len(arguments) <= 256
        or not all(isinstance(value, str) and "\0" not in value for value in arguments)
    ):
        raise GraphError("Batch job commands require 1 to 256 string arguments")
    spec = command_spec(arguments[0])
    if spec is None or spec.name not in MANIFEST_COMMANDS:
        raise GraphError("This command is not supported in batch manifests")
    if any(value.split("=", 1)[0] in _EXECUTION_FLAGS for value in arguments):
        raise GraphError("Set execution controls on run-manifest, not inside jobs")
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            args = build_parser().parse_args(arguments)
    except SystemExit as error:
        raise GraphError("Batch job has invalid command arguments") from error
    for field in (*args.positionals, "output"):
        value = getattr(args, field)
        if not isinstance(value, str):
            raise GraphError("Batch manifest paths must be strings")
        if "://" not in value and not value.startswith("file:"):
            setattr(args, field, str(root / value))
    plan, duration = _build_media_plan(args)
    try:
        return BatchJob(
            name, plan, expected_duration=duration, timeout=entry.get("timeout")
        )
    except (TypeError, ValueError) as error:
        raise GraphError(
            "Batch job timeout must be a positive finite number"
        ) from error


__all__ = ["load_batch_manifest"]
