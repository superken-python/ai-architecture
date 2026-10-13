"""Chuẩn hóa văn bản tiếng Việt để tìm kiếm và so khớp tên cột (DATA-06)."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

_SPACES = re.compile(r"\s+")


def normalize(value: Any) -> str:
    """NFC → chữ thường → bỏ dấu (đ → d) → gộp khoảng trắng.

    "  Thành   PHỐ " → "thanh pho"; "Mã ĐH" → "ma dh"; số 12 → "12".
    """
    if value is None:
        return ""
    text = unicodedata.normalize("NFC", str(value)).casefold().replace("đ", "d")
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    return _SPACES.sub(" ", text).strip()


def find_name(names: list[str], wanted: str | None) -> str | None:
    """Tìm tên (cột, trường) khớp `wanted` sau khi chuẩn hóa; không thấy thì trả None."""
    if not wanted:
        return None
    key = normalize(wanted)
    for name in names:
        if normalize(name) == key:
            return name
    return None
