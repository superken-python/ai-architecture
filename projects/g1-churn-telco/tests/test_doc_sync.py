"""Bài học Giai đoạn A (docs/03-giai-doan-a-nen-tang/) chép NGUYÊN VĂN code của dự án và lab.

Sửa code mà quên bài → test đỏ; chạy `uv run python scripts/sync_doc.py` để cập nhật bài. Mọi phần (hàm, lớp, biến cấp
module) của mọi module trong src/ và mọi script lab đều phải có mặt trong bài — không có code "bí mật" ngoài bài học.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import sync_doc as S  # noqa: E402

STAGE_A_LABS = [
    "biz-01-co-ban-framing-churn",
    "data-01-co-ban-kham-pha-du-lieu",
    "stat-02-co-ban-bootstrap",
    "data-03-trung-cap-ro-ri-du-lieu",
    "stat-05-trung-cap-nguong-chi-phi",
    "biz-03-trung-cap-phan-tich-loi",
    "ops-01-co-ban-dong-goi-api",
    "biz-04-co-ban-trinh-bay",
]
MUST_EMBED = [
    *(f"src/churn_telco/{p.name}" for p in sorted((S.PROJECT / "src" / "churn_telco").glob("*.py"))),
    *["Makefile", "Dockerfile", "docker-compose.yml", "pyproject.toml", ".env.example", ".gitignore", ".dockerignore"],
    *(f"labs/{lab}/{p.name}" for lab in STAGE_A_LABS for p in sorted((S.REPO / "labs" / lab).glob("*.py"))),
]
NOT_EMBEDDED = {"src/churn_telco/simulate.py", "src/churn_telco/__init__.py"}  # hệ nguồn giả lập: chép, không cần hiểu
EMBEDDED = [(doc.name, path, symbol, body) for doc in S.docs() for path, symbol, body in S.blocks(doc)]


def test_all_lessons_exist():
    names = [d.name for d in S.docs()]
    assert names[0] == "README.md" and len([n for n in names if n.startswith("a")]) == 8


def test_every_part_of_every_file_is_in_the_lessons():
    symbols: dict[str, list] = {}
    for _, path, symbol, _ in EMBEDDED:
        symbols.setdefault(path, []).append(symbol)
    missing = {}
    for path in [p for p in MUST_EMBED if p not in NOT_EMBEDDED]:
        if path not in symbols:
            missing[path] = "cả file"
        elif path.endswith(".py"):
            file = S.resolve(path)
            left = {name for name, _, _ in S.parts(file.read_text(encoding="utf-8"))} - S.covered(file, symbols[path])
            if left:
                missing[path] = sorted(left)
    assert not missing, f"Bài học còn thiếu: {missing}"


@pytest.mark.parametrize(("doc", "path", "symbol", "body"), EMBEDDED, ids=[f"{d}:{p}:{s}" for d, p, s, _ in EMBEDDED])
def test_lesson_block_matches_code(doc, path, symbol, body):
    assert body == S.segment(S.resolve(path), symbol), (
        f"{path} ({symbol or 'cả file'}) trong {doc} đã cũ — chạy sync_doc"
    )
