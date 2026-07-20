"""Create small local media files for Flowmpeg examples."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def _resolve_tool(value: str) -> str:
    path = shutil.which(value)
    if path is None:
        raise RuntimeError(f"Media tool was not found: {value}")
    return path


def _run(command: tuple[str, ...], timeout: float) -> None:
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
    if completed.returncode != 0:
        reason = completed.stderr.strip().splitlines()
        detail = reason[-1] if reason else f"exit code {completed.returncode}"
        raise RuntimeError(f"Media command failed: {detail[:400]}")


def generate(
    directory: Path,
    *,
    ffmpeg: str,
    ffprobe: str,
    overwrite: bool,
    timeout: float,
) -> dict[str, object]:
    """Generate the example files and return a small probe summary."""

    if timeout <= 0:
        raise ValueError("Timeout must be positive")
    ffmpeg_path = _resolve_tool(ffmpeg)
    ffprobe_path = _resolve_tool(ffprobe)
    directory.mkdir(parents=True, exist_ok=True)
    video = directory / "sample.mp4"
    second_video = directory / "second.mp4"
    silent_video = directory / "silent.mp4"
    voice = directory / "voice.wav"
    music = directory / "music.wav"
    cover = directory / "cover.jpg"
    logo = directory / "logo.png"
    captions = directory / "captions.srt"
    frames = tuple(directory / f"frame-{index:03}.png" for index in range(1, 5))
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
    existing = [path.name for path in targets if path.exists()]
    if existing and not overwrite:
        names = ", ".join(existing)
        raise RuntimeError(f"Output files already exist: {names}")
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
            str(directory / "frame-%03d.png"),
        ),
        timeout,
    )
    captions.write_text(
        "1\n00:00:00,000 --> 00:00:01,500\nFlowmpeg demo caption\n",
        encoding="utf-8",
        newline="\n",
    )
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
    if probe.returncode != 0:
        raise RuntimeError("FFprobe could not verify the generated video")
    data = json.loads(probe.stdout)
    return {
        "directory": str(directory.resolve()),
        "files": [path.name for path in targets],
        "video_duration": float(data["format"]["duration"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create small media files for Flowmpeg examples."
    )
    parser.add_argument("directory", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    try:
        result = generate(
            args.directory,
            ffmpeg=args.ffmpeg,
            ffprobe=args.ffprobe,
            overwrite=args.overwrite,
            timeout=args.timeout,
        )
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"make_demo_media: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
