"""Code trong tài liệu phải là nguyên văn file trong lab — sửa code mà quên sửa tài liệu thì test này đỏ.

Cập nhật tài liệu bằng `python sync_doc.py`. Mỗi khối bắt đầu bằng `# file: <đường dẫn>` (python) hoặc
`<!-- file: <đường dẫn> -->` (markdown).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
DOC = LAB.parents[1] / "docs" / "agent-radar" / "02-harness-agno-sang-langchain.md"
BLOCK = re.compile(r"^(`{3,})(?:python|markdown)\n(?:# file: |<!-- file: )(\S+?)(?: -->)?\n(.*?)\n\1$", re.S | re.M)


def blocks() -> list[tuple[str, str]]:
    return [(path, body) for _, path, body in BLOCK.findall(DOC.read_text(encoding="utf-8"))]


def test_doc_embeds_every_module():
    embedded = {path for path, _ in blocks()}
    modules = {p.relative_to(LAB).as_posix() for p in (LAB / "harness").glob("*.py") if p.name != "__init__.py"}
    assert modules <= embedded, f"Tài liệu thiếu: {sorted(modules - embedded)}"


@pytest.mark.parametrize(("path", "body"), blocks(), ids=lambda v: v if "/" in v or v.endswith(".py") else "")
def test_doc_block_matches_file(path: str, body: str):
    current = (LAB / path).read_text(encoding="utf-8").rstrip("\n")
    assert body == current, f"{path} trong tài liệu đã cũ — chạy python {LAB.name}/sync_doc.py"
