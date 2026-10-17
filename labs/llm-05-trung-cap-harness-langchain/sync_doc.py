"""Cập nhật các khối code trong tài liệu theo file hiện tại của lab (chạy sau khi sửa code).

    python labs/llm-05-trung-cap-harness-langchain/sync_doc.py

Mỗi khối bắt đầu bằng `# file: <đường dẫn>` (python) hoặc `<!-- file: <đường dẫn> -->` (markdown) được thay
bằng nội dung file đó. tests/test_doc_sync.py kiểm tra hai bên khớp nhau.
"""

from __future__ import annotations

import re
from pathlib import Path

LAB = Path(__file__).resolve().parent
DOC = LAB.parents[1] / "docs" / "agent-radar" / "02-harness-agno-sang-langchain.md"
BLOCK = re.compile(r"^(`{3,})(python|markdown)\n((?:# file: |<!-- file: )(\S+?)(?: -->)?)\n(.*?)\n\1$", re.S | re.M)


def sync(doc: Path = DOC) -> int:
    text = doc.read_text(encoding="utf-8")
    changed = 0

    def replace(m: re.Match) -> str:
        nonlocal changed
        fence, lang, marker, path, body = m.groups()
        current = (LAB / path).read_text(encoding="utf-8").rstrip("\n")
        changed += current != body
        return f"{fence}{lang}\n{marker}\n{current}\n{fence}"

    doc.write_text(BLOCK.sub(replace, text), encoding="utf-8")
    return changed


if __name__ == "__main__":
    print(f"Đã cập nhật {sync()} khối code trong {DOC.name}")
