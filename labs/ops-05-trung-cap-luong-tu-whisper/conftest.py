"""Fixture chung cho test của lab. Thư mục này được pytest đưa vào sys.path nên `import luong_tu` chạy được."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def g9_vtt() -> Path:
    """Phụ đề của video chữ cái (dự án g9): bộ đo mặc định của lab."""
    return ROOT / "projects" / "g9-video-chu-cai" / "media" / "phu-de.vtt"
