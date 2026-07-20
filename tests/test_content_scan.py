import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_repository_content_scan_passes() -> None:
    completed = subprocess.run(
        (sys.executable, "scripts/content_scan.py"),
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout
