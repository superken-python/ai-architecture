"""Đồng bộ khối code trong bài học Giai đoạn A (docs/03-giai-doan-a-nen-tang/) với file thật của dự án và lab.

    uv run python scripts/sync_doc.py          # chạy trong projects/g1-churn-telco sau khi sửa code

Một khối code đứng ngay sau dòng nhãn:
    **File: `src/churn_telco/clean.py`**                    → cả file
    **File: `src/churn_telco/clean.py` · `clean_customers`** → một hàm/lớp/biến cấp module (+ chú thích ngay trên)
    **File: `src/churn_telco/features.py` · `KEYS…NUMERIC`** → từ KEYS tới hết NUMERIC
    **File: `src/churn_telco/clean.py` · `đầu file`**        → docstring + import đầu module
Đường dẫn bắt đầu bằng `labs/` hoặc `.github/` tính từ gốc repo, còn lại tính từ thư mục dự án.
tests/test_doc_sync.py kiểm tra tài liệu khớp code và mọi phần của mỗi module đều có mặt trong bài.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parents[1]
LESSONS = REPO / "docs" / "03-giai-doan-a-nen-tang"
BLOCK = re.compile(r"^(\*\*File: `([^`]+)`(?: · `([^`]+)`)?\*\*[^\n]*\n\n)(`{3,})(\w*)\n(.*?)\n\4$", re.S | re.M)
HEADER = "đầu file"


def resolve(path: str) -> Path:
    return REPO / path if path.startswith(("labs/", ".github/")) else PROJECT / path


def docs() -> list[Path]:
    return sorted(LESSONS.glob("*.md"))


def _names(node: ast.stmt) -> list[str]:
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return [node.name]
    if isinstance(node, ast.Assign):
        return [t.id for t in node.targets if isinstance(t, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target.id]
    if isinstance(node, ast.If) and "__name__" in ast.unparse(node.test):
        return ["__main__"]
    return []


def _is_header(node: ast.stmt) -> bool:
    docstring = (
        isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
    )
    return docstring or isinstance(node, ast.Import | ast.ImportFrom)


def _header_size(body: list[ast.stmt]) -> int:
    """Số câu lệnh của phần đầu: docstring + import, kể cả câu lệnh xen giữa các import (vd. matplotlib.use)."""
    size = 0
    for i, node in enumerate(body):
        if not (_is_header(node) or isinstance(node, ast.Expr)):
            break
        if _is_header(node):
            size = i + 1
    return size


def parts(source: str) -> list[tuple[str, int, int]]:
    """Các phần cấp module theo thứ tự: (tên, dòng đầu, dòng cuối) — dòng tính từ 1, gồm chú thích ngay phía trên."""
    lines = source.splitlines()
    body = ast.parse(source).body
    n_header = _header_size(body)
    header_end = body[n_header - 1].end_lineno if n_header else 0
    result: list[tuple[str, int, int]] = []
    for node in body[n_header:]:
        start = min([node.lineno, *(d.lineno for d in getattr(node, "decorator_list", []))])
        while start > 1 and lines[start - 2].lstrip().startswith("#"):
            start -= 1
        names = _names(node) or [f"<dòng {node.lineno}>"]
        result.append((names[0], start, node.end_lineno))
    return ([(HEADER, 1, header_end)] if header_end else []) + result


def segment(path: Path, symbol: str | None) -> str:
    source = path.read_text(encoding="utf-8")
    if symbol is None:
        return source.rstrip("\n")
    first, _, last = symbol.partition("…")
    found = {name: (start, end) for name, start, end in parts(source)}
    if first not in found or (last and last not in found):
        raise KeyError(f"{path.name}: không có phần '{symbol}'")
    start, end = found[first][0], found[last or first][1]
    return "\n".join(source.splitlines()[start - 1 : end])


def covered(path: Path, symbols: list[str | None]) -> set[str]:
    """Tên các phần của file đã có mặt trong tài liệu."""
    if None in symbols:
        return {name for name, _, _ in parts(path.read_text(encoding="utf-8"))}
    names = [name for name, _, _ in parts(path.read_text(encoding="utf-8"))]
    seen: set[str] = set()
    for symbol in symbols:
        first, _, last = symbol.partition("…")
        i, j = names.index(first), names.index(last or first)
        seen.update(names[i : j + 1])
    return seen


def blocks(doc: Path) -> list[tuple[str, str | None, str]]:
    """(đường dẫn, phần, nội dung) của mọi khối code có nhãn File trong một bài."""
    return [(path, symbol or None, body) for _, path, symbol, _, _, body in BLOCK.findall(doc.read_text("utf-8"))]


def sync(doc: Path) -> int:
    text = doc.read_text(encoding="utf-8")
    changed = 0

    def replace(m: re.Match) -> str:
        nonlocal changed
        label, path, symbol, fence, lang, body = m.groups()
        current = segment(resolve(path), symbol or None)
        changed += current != body
        return f"{label}{fence}{lang}\n{current}\n{fence}"

    doc.write_text(BLOCK.sub(replace, text), encoding="utf-8")
    return changed


if __name__ == "__main__":
    for doc in docs():
        print(f"{doc.name}: cập nhật {sync(doc)} khối code")
