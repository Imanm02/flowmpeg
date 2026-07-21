"""Generate small local media inputs for Flowmpeg examples."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from flowmpeg.diagnostics import redact_text
from flowmpeg.errors import (
    BinaryNotFoundError,
    FlowmpegError,
    JobTimeoutError,
    OutputExistsError,
)


@dataclass(frozen=True, slots=True)
class DemoMediaResult:
    """Files created for one local demo workspace."""

    directory: Path
    files: tuple[Path, ...]
    video_duration: float

    def as_dict(self) -> dict[str, object]:
        """Return stable JSON-ready result fields."""

        return {
            "directory": str(self.directory),
            "files": [path.name for path in self.files],
            "video_duration": self.video_duration,
        }


def _resolve_tool(value: str, expected: str) -> str:
    path = shutil.which(value)
    if path is None:
        raise BinaryNotFoundError(
            f"The {expected} executable was not found: {value}",
            tool=expected,
        )
    return path


def _run(command: tuple[str, ...], timeout: float) -> None:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as error:
        raise JobTimeoutError(
            f"Demo media generation exceeded {timeout:g} seconds"
        ) from error
    except OSError as error:
        raise FlowmpegError(redact_text(str(error))) from error
    if completed.returncode != 0:
        lines = redact_text(completed.stderr).strip().splitlines()
        detail = lines[-1] if lines else f"exit code {completed.returncode}"
        raise FlowmpegError(f"Demo media generation failed: {detail[:400]}")


def generate_demo_media(
    directory: str | Path,
    *,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
    overwrite: bool = False,
    timeout: float = 30.0,
) -> DemoMediaResult:
    """Create a small set of inputs for local examples."""

    if isinstance(timeout, bool) or not isinstance(timeout, int | float):
        raise TypeError("timeout must be a number")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    ffmpeg_path = _resolve_tool(ffmpeg, "ffmpeg")
    ffprobe_path = _resolve_tool(ffprobe, "ffprobe")
    destination = Path(directory).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    video = destination / "sample.mp4"
    second_video = destination / "second.mp4"
    silent_video = destination / "silent.mp4"
    voice = destination / "voice.wav"
    music = destination / "music.wav"
    cover = destination / "cover.jpg"
    logo = destination / "logo.png"
    captions = destination / "captions.srt"
    frames = tuple(destination / f"frame-{index:03}.png" for index in range(1, 5))
    targets = (
        video,
        second_video,
        silent_video,
        voice,
        music,
        cover,
        logo,
        captions,
        *frames,
    )
    existing = tuple(path for path in targets if path.exists())
    if existing and not overwrite:
        names = ", ".join(path.name for path in existing)
        raise OutputExistsError(f"Demo files already exist: {names}")
    replace = "-y" if overwrite else "-n"

    _run(
        (
            ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            replace,
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x180:rate=24:duration=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-metadata",
            "title=Flowmpeg demo source",
            "-shortest",
            str(video),
        ),
        timeout,
    )
    _run(
        (
            ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            replace,
            "-f",
            "lavfi",
            "-i",
            "smptebars=size=320x180:rate=24:duration=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=660:sample_rate=48000:duration=2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(second_video),
        ),
        timeout,
    )
    _run(
        (
            ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            replace,
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x180:rate=24:duration=2",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(silent_video),
        ),
        timeout,
    )
    _run(
        (
            ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            replace,
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=220:sample_rate=48000:duration=2",
            str(voice),
        ),
        timeout,
    )
    _run(
        (
            ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            replace,
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=330:sample_rate=48000:duration=2",
            str(music),
        ),
        timeout,
    )
    _run(
        (
            ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            replace,
            "-f",
            "lavfi",
            "-i",
            "color=c=0x1f2937:s=640x360:d=0.1",
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(cover),
        ),
        timeout,
    )
    _run(
        (
            ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            replace,
            "-f",
            "lavfi",
            "-i",
            (
                "color=c=black@0.0:s=96x96:d=0.1,format=rgba,"
                "drawbox=x=8:y=8:w=80:h=80:color=0x38bdf8@0.85:t=fill"
            ),
            "-frames:v",
            "1",
            str(logo),
        ),
        timeout,
    )
    _run(
        (
            ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            replace,
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x180:rate=2:duration=2",
            "-frames:v",
            "4",
            "-start_number",
            "1",
            str(destination / "frame-%03d.png"),
        ),
        timeout,
    )
    captions.write_text(
        "1\n00:00:00,000 --> 00:00:01,500\nFlowmpeg demo caption\n",
        encoding="utf-8",
        newline="\n",
    )
    try:
        probe = subprocess.run(
            (
                ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(video),
            ),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as error:
        raise JobTimeoutError(
            f"Demo media verification exceeded {timeout:g} seconds"
        ) from error
    except OSError as error:
        raise FlowmpegError(redact_text(str(error))) from error
    if probe.returncode != 0:
        raise FlowmpegError("FFprobe could not verify the generated video")
    data = json.loads(probe.stdout)
    return DemoMediaResult(
        directory=destination,
        files=targets,
        video_duration=float(data["format"]["duration"]),
    )


__all__ = ["DemoMediaResult", "generate_demo_media"]
