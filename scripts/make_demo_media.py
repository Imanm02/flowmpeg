"""Create small local media files for Flowmpeg examples."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowmpeg.demo import generate_demo_media  # noqa: E402
from flowmpeg.errors import FlowmpegError  # noqa: E402


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
        result = generate_demo_media(
            args.directory,
            ffmpeg=args.ffmpeg,
            ffprobe=args.ffprobe,
            overwrite=args.overwrite,
            timeout=args.timeout,
        )
    except (FlowmpegError, OSError, TypeError, ValueError) as error:
        print(f"make_demo_media: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
