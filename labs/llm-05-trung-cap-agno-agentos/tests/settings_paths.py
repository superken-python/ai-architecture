"""Đường dẫn file kết quả trong project tham chiếu, dùng chung cho test."""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def storage_file(*parts: str) -> Path:
    return ROOT.joinpath("storage", *parts)


def clean_storage(report_id: str) -> None:
    shutil.rmtree(ROOT / "storage" / report_id, ignore_errors=True)
