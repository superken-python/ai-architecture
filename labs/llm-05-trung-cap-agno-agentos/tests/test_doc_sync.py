"""Code trong tài liệu Lab 01 phải là nguyên văn file của project — sửa code mà quên tài liệu thì test này đỏ.

Cập nhật tài liệu bằng `python sync_doc.py`.
"""

import pytest

from sync_doc import DOCS, LAB, blocks

EMBEDDED = [(doc.name, path, body) for doc in DOCS for path, body in blocks(doc)]
MUST_EMBED = {
    "agno_cli.py",
    "mcp_db_server.py",
    "mock_llm.py",
    "conftest.py",
    *(p.relative_to(LAB).as_posix() for p in (LAB / "agno_lab").glob("p*.py")),
    "agno_lab/settings.py",
    *(p.relative_to(LAB).as_posix() for p in (LAB / "tests").glob("*.py") if p.name != "test_doc_sync.py"),
}


def test_every_module_and_test_is_in_the_docs():
    missing = MUST_EMBED - {path for _, path, _ in EMBEDDED}
    assert not missing, f"Tài liệu thiếu: {sorted(missing)}"


@pytest.mark.parametrize(("doc", "path", "body"), EMBEDDED, ids=[f"{d}:{p}" for d, p, _ in EMBEDDED])
def test_doc_block_matches_file(doc: str, path: str, body: str):
    current = (LAB / path).read_text(encoding="utf-8").rstrip("\n")
    assert body == current, f"{path} trong {doc} đã cũ — chạy python sync_doc.py"
