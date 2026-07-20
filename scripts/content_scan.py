"""Check repository text for credential and writing-policy violations."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".cfg",
    ".gitignore",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
TEXT_NAMES = {"LICENSE"}

_term_parts = (
    ("compre", "hensive"),
    ("seam", "less"),
    ("lever", "age"),
    ("util", "ize"),
    ("ro", "bust"),
    ("del", "ve"),
    ("tape", "stry"),
    ("empower", "ing"),
    ("har", "ness"),
    ("intri", "cate"),
    ("nu", "anced"),
)
_phrase_parts = (
    ("whether you", "'re"),
    ("dive ", "into"),
    ("elevate ", "your"),
    ("streamline ", "your"),
    ("in con", "clusion"),
    ("over", "all,"),
    ("further", "more,"),
    ("more", "over,"),
    ("addition", "ally,"),
    ("in sum", "mary"),
    ("it's worth ", "noting"),
    ("navigate ", "the"),
)
_prohibited_text = tuple("".join(parts) for parts in (*_term_parts, *_phrase_parts))
_prohibited_pattern = re.compile(
    "|".join(re.escape(value) for value in _prohibited_text),
    re.IGNORECASE,
)
_email_pattern = re.compile(
    r"[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})",
    re.IGNORECASE,
)
_secret_patterns = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"Bearer\s+eyJ[A-Za-z0-9._-]+", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----"),
    re.compile(
        r"(?i)(?:api[_-]?key|client[_-]?secret|password|access[_-]?token)"
        r"\s*[:=]\s*['\"]?(?!REDACT_ME\b|<redacted>\b|example\b)"
        r"[A-Za-z0-9/+_.-]{8,}"
    ),
)
_emoji_pattern = re.compile("[\U0001f1e6-\U0001f1ff\U0001f300-\U0001faff\u2600-\u27bf]")


def _repository_paths() -> tuple[Path, ...]:
    completed = subprocess.run(
        ("git", "ls-files", "--cached", "--others", "--exclude-standard"),
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    paths = []
    for value in completed.stdout.splitlines():
        path = ROOT / value
        if path.name in TEXT_NAMES or path.suffix.lower() in TEXT_SUFFIXES:
            paths.append(path)
    return tuple(paths)


def _line_issues(path: Path, text: str) -> list[str]:
    issues: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if "\u2013" in line or "\u2014" in line:
            issues.append(f"{path}:{number}: long dash character")
        if _prohibited_pattern.search(line):
            issues.append(f"{path}:{number}: prohibited writing term")
        if _emoji_pattern.search(line):
            issues.append(f"{path}:{number}: emoji")
        for pattern in _secret_patterns:
            if pattern.search(line):
                issues.append(f"{path}:{number}: possible credential")
                break
        email = _email_pattern.search(line)
        if email is not None and email.group(1).lower() not in {
            "example.com",
            "example.net",
            "example.org",
        }:
            issues.append(f"{path}:{number}: non-placeholder email")
    if path.suffix.lower() == ".md":
        rules = sum(line.strip() == "---" for line in text.splitlines())
        if rules > 1:
            issues.append(f"{path}: more than one Markdown horizontal rule")
    return issues


def main() -> int:
    issues: list[str] = []
    for path in _repository_paths():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        issues.extend(_line_issues(path.relative_to(ROOT), text))
    if issues:
        print("\n".join(issues))
        return 1
    print("Content scan passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
