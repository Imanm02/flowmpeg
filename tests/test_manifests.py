from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from flowmpeg import GraphError, load_batch_manifest, probe
from flowmpeg.cli import main


def _manifest(tmp_path: Path, job: object) -> Path:
    path = tmp_path / "jobs.json"
    path.write_text(json.dumps({"schema_version": 1, "jobs": [job]}), encoding="utf-8")
    return path


def test_manifest_resolves_paths_relative_to_itself(tmp_path: Path) -> None:
    path = _manifest(
        tmp_path,
        {
            "name": "Phone",
            "command": ["shrink", "phone.mov", "-o", "small.mp4"],
            "timeout": 30,
        },
    )
    (job,) = load_batch_manifest(path)
    assert job.name == "Phone"
    assert job.timeout == 30
    assert job.plan.outputs[0].destination == str(tmp_path / "small.mp4")
    assert str(tmp_path / "phone.mov") in job.plan.raw_argv()
    assert not (tmp_path / "small.mp4").exists()


@pytest.mark.parametrize(
    "arguments",
    [
        ["setup", "--install", "--yes"],
        ["ui"],
        ["manifest", "other.json"],
        ["shrink", "in.mov", "-o", "out.mp4", "--overwrite"],
        ["shrink", "in.mov", "-o", "out.mp4", "--ffmpeg=other"],
        ["trim", "in.mov", "-o", "out.mp4", "--bad-option"],
        ["shrink", "--help"],
        [],
        [True],
    ],
)
def test_manifest_rejects_unsupported_commands(
    tmp_path: Path, arguments: object
) -> None:
    path = _manifest(tmp_path, {"name": "Job", "command": arguments})
    with pytest.raises(GraphError):
        load_batch_manifest(path)


@pytest.mark.parametrize("timeout", [True, 0, -1, float("inf"), "30"])
def test_manifest_rejects_bad_timeout(tmp_path: Path, timeout: object) -> None:
    path = _manifest(
        tmp_path,
        {
            "name": "Job",
            "command": ["convert", "in.mov", "-o", "out.mp4"],
            "timeout": timeout,
        },
    )
    with pytest.raises(GraphError, match="timeout"):
        load_batch_manifest(path)


@pytest.mark.parametrize(
    "text",
    [
        '{"schema_version":true,"jobs":[]}',
        '{"schema_version":1,"jobs":[]}',
        '{"schema_version":1,"schema_version":1,"jobs":[]}',
        '{"schema_version":2,"jobs":[]}',
        '{"schema_version":1,"jobs":[],"unknown":0}',
        "[]",
        "{",
        "x" * 1_048_577,
    ],
    ids=[
        "boolean-version",
        "empty",
        "duplicate-key",
        "future-version",
        "unknown",
        "array",
        "invalid-json",
        "oversized",
    ],
)
def test_manifest_rejects_invalid_documents(tmp_path: Path, text: str) -> None:
    path = tmp_path / "jobs.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(GraphError):
        load_batch_manifest(path)


def test_manifest_rejects_duplicate_names_before_execution(tmp_path: Path) -> None:
    job = {"name": "Same", "command": ["convert", "in.mov", "-o", "out.mp4"]}
    path = tmp_path / "jobs.json"
    path.write_text(
        json.dumps({"schema_version": 1, "jobs": [job, job]}), encoding="utf-8"
    )
    with pytest.raises(GraphError, match="unique"):
        load_batch_manifest(path)


def test_manifest_cli_dry_run_is_json_without_output_files(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _manifest(
        tmp_path,
        {
            "name": "Phone",
            "command": [
                "shrink",
                "phone.mov",
                "--keep-size",
                "-o",
                "small.mp4",
            ],
        },
    )
    assert main(["manifest", str(path), "--dry-run", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["jobs"][0]["name"] == "Phone"
    assert report["jobs"][0]["outputs"] == [str(tmp_path / "small.mp4")]
    assert not (tmp_path / "small.mp4").exists()


def test_manifest_cli_protects_existing_files(tmp_path: Path) -> None:
    path = _manifest(
        tmp_path,
        {
            "name": "Phone",
            "command": ["shrink", "in.mov", "-o", "small.mp4"],
        },
    )
    target = tmp_path / "small.mp4"
    target.write_bytes(b"keep this file")
    assert main(["manifest", str(path)]) == 4
    assert target.read_bytes() == b"keep this file"


@pytest.mark.integration
def test_manifest_runs_relative_inputs_from_another_directory(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required")
    source = tmp_path / "in.mov"
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=64x48:duration=0.2",
            "-c:v",
            "mpeg4",
            str(source),
        ],
        check=True,
        timeout=10,
    )
    path = _manifest(
        tmp_path,
        {
            "name": "Phone",
            "command": [
                "shrink",
                "in.mov",
                "--codec",
                "h264",
                "--max-height",
                "24",
                "-o",
                "small.mp4",
            ],
        },
    )
    assert main(["manifest", str(path), "--no-progress"]) == 0
    video = probe(tmp_path / "small.mp4").video_streams[0]
    assert (video.width, video.height) == (32, 24)


def test_documented_manifest_builds(tmp_path: Path) -> None:
    text = (Path(__file__).parents[1] / "docs" / "batch-jobs.md").read_text(
        encoding="utf-8"
    )
    example = text.split("```json\n", 1)[1].split("```", 1)[0]
    path = tmp_path / "jobs.json"
    path.write_text(example, encoding="utf-8")
    assert len(load_batch_manifest(path)) == 2
