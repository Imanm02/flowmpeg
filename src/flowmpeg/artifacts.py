"""Owned multi-file HLS and DASH delivery workflows."""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import uuid
import warnings
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from flowmpeg.errors import GraphError, OutputExistsError
from flowmpeg.pathing import same_destination
from flowmpeg.plan import Plan, output
from flowmpeg.progress import Progress
from flowmpeg.runner import RunResult
from flowmpeg.streams import Stream, input

ArtifactKind = Literal["hls", "dash"]
_MARKER_NAME = ".flowmpeg-artifacts.json"
_BITRATE = re.compile(r"(\d+(?:\.\d+)?)[kKmMgG]?")


@dataclass(frozen=True, slots=True)
class ArtifactSet:
    """Completed manifest and media files owned by one workflow."""

    kind: ArtifactKind
    root: str
    manifest: str
    files: tuple[str, ...]
    encoding: RunResult


@dataclass(frozen=True, slots=True)
class SegmentWorkflow:
    """One staged HLS or DASH package with explicit directory ownership."""

    kind: ArtifactKind
    source: str
    destination: str
    segment_duration: float
    crf: int = 23
    audio_bitrate: str = "128k"
    include_audio: bool = True
    overwrite: bool = False

    def __post_init__(self) -> None:
        _validate_workflow(self)

    @property
    def manifest_name(self) -> str:
        """Return the fixed manifest name for this package kind."""

        return "index.m3u8" if self.kind == "hls" else "manifest.mpd"

    def plan(self, destination: str | os.PathLike[str] | None = None) -> Plan:
        """Build the encoding plan without creating the artifact directory."""

        root = Path(self.destination if destination is None else destination).resolve()
        manifest = root / self.manifest_name
        media = input(_plan_source(self.source))
        streams: list[Stream] = [media.video()]
        if self.include_audio:
            streams.append(media.audio(optional=True))
        args = self._output_args()
        return output(*streams, to=manifest, args=args).overwrite(False)

    def explain(self, ffmpeg: str = "ffmpeg") -> str:
        """Describe ownership and the encoding plan without creating files."""

        return "\n".join(
            (
                f"Artifact kind: {self.kind}",
                f"Owned directory: {self.destination}",
                f"Manifest: {self.manifest_name}",
                f"Segment duration: {self.segment_duration:g}s",
                f"Overwrite owned set: {'yes' if self.overwrite else 'no'}",
                f"Command: {self.plan().command(ffmpeg)}",
            )
        )

    def run(
        self,
        *,
        ffmpeg: str = "ffmpeg",
        on_progress: Callable[[Progress], None] | None = None,
        expected_duration: float | None = None,
        timeout: float | None = None,
    ) -> ArtifactSet:
        """Encode into a staged owned directory and publish it on success."""

        target = Path(self.destination).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        existing_owned = _existing_owned_kind(target)
        if existing_owned is not None:
            if existing_owned != self.kind:
                raise OutputExistsError(
                    f"Artifact directory belongs to {existing_owned}: {target}"
                )
            if not self.overwrite:
                raise OutputExistsError(f"Artifact directory already exists: {target}")
            work_root = _sibling(target, "stage")
        elif os.path.lexists(target):
            raise OutputExistsError(
                f"Artifact directory is not Flowmpeg-owned: {target}"
            )
        else:
            work_root = target

        work_root.mkdir()
        published = False
        try:
            encoding = self.plan(work_root).run(
                ffmpeg=ffmpeg,
                cwd=work_root,
                on_progress=on_progress,
                expected_duration=expected_duration,
                timeout=timeout,
            )
            files = _artifact_files(work_root)
            manifest = work_root / self.manifest_name
            if not manifest.is_file():
                raise GraphError(f"FFmpeg did not create {self.manifest_name}")
            _write_marker(work_root, self.kind, self.manifest_name, files)
            if work_root != target:
                _publish_replacement(work_root, target)
            published = True
        finally:
            if not published and work_root.exists():
                _remove_created_tree(work_root)

        final_files = tuple(
            str(target / relative) for relative in _artifact_files(target)
        )
        final_manifest = str(target / self.manifest_name)
        final_encoding = replace(encoding, outputs=(final_manifest,))
        return ArtifactSet(
            self.kind,
            str(target),
            final_manifest,
            final_files,
            final_encoding,
        )

    def _output_args(self) -> tuple[str, ...]:
        base: tuple[str, ...] = (
            "-c:v",
            "libx264",
            "-crf",
            str(self.crf),
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-force_key_frames",
            f"expr:gte(t,n_forced*{self.segment_duration:g})",
        )
        if self.include_audio:
            base += ("-c:a", "aac", "-b:a", self.audio_bitrate)
        if self.kind == "hls":
            return (
                *base,
                "-f",
                "hls",
                "-hls_time",
                f"{self.segment_duration:g}",
                "-hls_playlist_type",
                "vod",
                "-hls_segment_filename",
                "segment-%05d.ts",
            )
        return (
            *base,
            "-f",
            "dash",
            "-seg_duration",
            f"{self.segment_duration:g}",
            "-use_template",
            "1",
            "-use_timeline",
            "1",
            "-init_seg_name",
            "init-$RepresentationID$.m4s",
            "-media_seg_name",
            "chunk-$RepresentationID$-$Number%05d$.m4s",
        )


def hls_package(
    source: str | os.PathLike[str],
    destination: str | os.PathLike[str],
    *,
    segment_duration: float = 6,
    crf: int = 23,
    audio_bitrate: str = "128k",
    include_audio: bool = True,
    overwrite: bool = False,
) -> SegmentWorkflow:
    """Build an owned HLS video-on-demand workflow."""

    return SegmentWorkflow(
        "hls",
        os.fspath(source),
        os.fspath(destination),
        segment_duration,
        crf,
        audio_bitrate,
        include_audio,
        overwrite,
    )


def dash_package(
    source: str | os.PathLike[str],
    destination: str | os.PathLike[str],
    *,
    segment_duration: float = 4,
    crf: int = 23,
    audio_bitrate: str = "128k",
    include_audio: bool = True,
    overwrite: bool = False,
) -> SegmentWorkflow:
    """Build an owned MPEG-DASH workflow."""

    return SegmentWorkflow(
        "dash",
        os.fspath(source),
        os.fspath(destination),
        segment_duration,
        crf,
        audio_bitrate,
        include_audio,
        overwrite,
    )


def _validate_workflow(workflow: SegmentWorkflow) -> None:
    if workflow.kind not in {"hls", "dash"}:
        raise GraphError(f"Unknown artifact kind: {workflow.kind}")
    if not workflow.source or workflow.source.startswith("-"):
        raise GraphError("Artifact sources cannot be empty or start with a dash")
    if not workflow.destination or workflow.destination.startswith("-"):
        raise GraphError("Artifact directories cannot be empty or start with a dash")
    if "://" in workflow.destination or workflow.destination.startswith("file:"):
        raise GraphError("Artifact directories must use local filesystem paths")
    if same_destination(workflow.source, workflow.destination):
        raise GraphError("An artifact directory cannot replace its input")
    if (
        isinstance(workflow.segment_duration, bool)
        or not isinstance(workflow.segment_duration, int | float)
        or not math.isfinite(workflow.segment_duration)
        or workflow.segment_duration <= 0
        or workflow.segment_duration > 3_600
    ):
        raise GraphError("Segment duration must be above zero and at most 3600")
    if isinstance(workflow.crf, bool) or not isinstance(workflow.crf, int):
        raise GraphError("CRF must be an integer from 0 through 51")
    if workflow.crf < 0 or workflow.crf > 51:
        raise GraphError("CRF must be an integer from 0 through 51")
    bitrate_match = (
        _BITRATE.fullmatch(workflow.audio_bitrate)
        if isinstance(workflow.audio_bitrate, str)
        else None
    )
    if bitrate_match is None:
        raise GraphError("Audio bitrate must be a positive value such as 128k")
    if float(bitrate_match.group(1)) <= 0:
        raise GraphError("Audio bitrate must be a positive value such as 128k")
    if not isinstance(workflow.include_audio, bool):
        raise GraphError("Audio inclusion must be Boolean")
    if not isinstance(workflow.overwrite, bool):
        raise GraphError("Overwrite state must be Boolean")


def _plan_source(source: str) -> str:
    if "://" in source or source.startswith("file:"):
        return source
    return str(Path(source).resolve())


def _existing_owned_kind(root: Path) -> ArtifactKind | None:
    if not os.path.lexists(root):
        return None
    if root.is_symlink() or not root.is_dir():
        return None
    marker = root / _MARKER_NAME
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        return None
    kind = data.get("kind")
    return kind if kind in {"hls", "dash"} else None


def _artifact_files(root: Path) -> tuple[str, ...]:
    return tuple(
        path.relative_to(root).as_posix()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != _MARKER_NAME
    )


def _write_marker(
    root: Path,
    kind: ArtifactKind,
    manifest: str,
    files: tuple[str, ...],
) -> None:
    data = {
        "schema_version": 1,
        "kind": kind,
        "manifest": manifest,
        "files": files,
    }
    (root / _MARKER_NAME).write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _publish_replacement(stage: Path, target: Path) -> None:
    backup = _sibling(target, "backup")
    target.rename(backup)
    try:
        stage.rename(target)
    except BaseException:
        backup.rename(target)
        raise
    try:
        _remove_created_tree(backup)
    except OSError as error:
        warnings.warn(
            f"Could not remove replaced artifact backup: {backup}: {error}",
            RuntimeWarning,
            stacklevel=2,
        )


def _sibling(target: Path, label: str) -> Path:
    return target.with_name(f".{target.name}.flowmpeg-{label}-{uuid.uuid4().hex}")


def _remove_created_tree(root: Path) -> None:
    if root.is_symlink():
        raise OSError(f"Refusing to remove artifact symlink: {root}")
    shutil.rmtree(root)


__all__ = [
    "ArtifactKind",
    "ArtifactSet",
    "SegmentWorkflow",
    "dash_package",
    "hls_package",
]
