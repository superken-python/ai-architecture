"""Đọc giá trị ngày và số theo cách người Việt hay nhập (dùng chung cho API dữ liệu và workbook)."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

_THOUSANDS_DOT = re.compile(r"^-?\d{1,3}(\.\d{3})+$")


def parse_date(value: Any) -> date | None:
    """Nhận date/datetime, '2026-09-28', '28/09/2026' hoặc '28-09-2026'; không phải ngày → None."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def to_number(value: Any) -> float | None:
    """'1.234.567' → 1234567; '1.234,5' → 1234.5; '1,234.5' → 1234.5; '12,5' → 12.5; không phải số → None."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip().replace(" ", "").replace(" ", "")
    if not text:
        return None
    if "," in text and "." in text:
        # dấu xuất hiện sau cùng là dấu thập phân
        comma_decimal = text.rfind(",") > text.rfind(".")
        text = text.replace(".", "").replace(",", ".") if comma_decimal else text.replace(",", "")
    elif "," in text:
        text = (
            text.replace(",", ".") if text.count(",") == 1 and len(text.split(",")[1]) != 3 else text.replace(",", "")
        )
    elif _THOUSANDS_DOT.match(text):
        text = text.replace(".", "")
    try:
        return float(text)
    except ValueError:
        return None
