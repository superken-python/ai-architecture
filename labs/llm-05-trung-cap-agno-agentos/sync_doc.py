"""Cập nhật các khối code trong tài liệu Lab 01 theo file hiện tại của project (chạy sau khi sửa code).

    python labs/llm-05-trung-cap-agno-agentos/sync_doc.py

Khối code đứng ngay sau dòng **File: `<đường dẫn>`** (cùng kiểu với Lab 00) được thay bằng nội dung file đó.
tests/test_doc_sync.py kiểm tra tài liệu và code khớp nhau.
"""

from __future__ import annotations

import re
from pathlib import Path

LAB = Path(__file__).resolve().parent
GUIDES = LAB.parents[1] / "docs" / "self-practices"
DOCS = [GUIDES / "guide_01_agno.md", *sorted((GUIDES / "agno").glob("*.md"))]
BLOCK = re.compile(r"^(\*\*File: `([^`]+)`[^\n]*\*\*\n\n)(`{3,})(\w*)\n(.*?)\n\3$", re.S | re.M)


def blocks(doc: Path) -> list[tuple[str, str]]:
    """(đường dẫn, nội dung) của mọi khối code có nhãn File trong tài liệu."""
    return [(path, body) for _, path, _, _, body in BLOCK.findall(doc.read_text(encoding="utf-8"))]


def sync(doc: Path) -> int:
    text = doc.read_text(encoding="utf-8")
    changed = 0

    def replace(m: re.Match) -> str:
        nonlocal changed
        label, path, fence, lang, body = m.groups()
        current = (LAB / path).read_text(encoding="utf-8").rstrip("\n")
        changed += current != body
        return f"{label}{fence}{lang}\n{current}\n{fence}"

    doc.write_text(BLOCK.sub(replace, text), encoding="utf-8")
    return changed


if __name__ == "__main__":
    for doc in DOCS:
        print(f"{doc.name}: cập nhật {sync(doc)} khối code")
