"""Mọi liên kết tương đối trong tài liệu Markdown phải trỏ tới file và anchor có thật."""

import re
from functools import cache
from pathlib import Path
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".venv", ".git", "templates", "node_modules"}
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
EXPLICIT_ANCHOR = re.compile(r'<a\s+(?:id|name)="([^"]+)"')
FENCE = re.compile(r"^\s*(```|~~~)")


def markdown_files() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*.md") if not SKIP_DIRS & set(p.relative_to(ROOT).parts))


def github_slug(heading: str) -> str:
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)  # bỏ cú pháp link, giữ chữ
    text = re.sub(r"[`*_]", "", text).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def strip_code(text: str) -> list[str]:
    lines, in_fence = [], False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            lines.append(re.sub(r"`[^`]*`", "", line))
    return lines


@cache
def anchors(path: Path) -> set[str]:
    found: set[str] = set()
    counts: dict[str, int] = {}
    for line in strip_code(path.read_text(encoding="utf-8")):
        found.update(EXPLICIT_ANCHOR.findall(line))
        m = HEADING.match(line)
        if m:
            slug = github_slug(m.group(1))
            n = counts.get(slug, 0)
            found.add(slug if n == 0 else f"{slug}-{n}")
            counts[slug] = n + 1
    return found


@pytest.mark.parametrize("md", markdown_files(), ids=lambda p: str(p.relative_to(ROOT)))
def test_relative_links_resolve(md: Path):
    broken = []
    for line in strip_code(md.read_text(encoding="utf-8")):
        for target in LINK.findall(line):
            if re.match(r"^[a-z]+:", target):  # http:, https:, mailto:
                continue
            path_part, _, anchor = target.partition("#")
            dest = (md.parent / unquote(path_part)).resolve() if path_part else md
            if not dest.exists():
                broken.append(f"{target} (không có file)")
            elif anchor and dest.suffix == ".md" and unquote(anchor) not in anchors(dest):
                broken.append(f"{target} (không có anchor)")
    assert not broken, "Liên kết hỏng:\n  " + "\n  ".join(broken)
