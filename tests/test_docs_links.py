"""Mọi liên kết tương đối trong tài liệu Markdown phải trỏ tới file và anchor có thật."""

import re
from functools import cache
from pathlib import Path
from urllib.parse import unquote

import pytest

from aiarch.docview import markdown_anchors

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".venv", ".git", "templates", "node_modules"}
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
FENCE = re.compile(r"^\s*(```|~~~)")


def markdown_files() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*.md") if not SKIP_DIRS & set(p.relative_to(ROOT).parts))


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
    # Cùng thuật toán với GitHub và khung xem tài liệu của trang web (aiarch.docview).
    return markdown_anchors(path.read_text(encoding="utf-8"))


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
