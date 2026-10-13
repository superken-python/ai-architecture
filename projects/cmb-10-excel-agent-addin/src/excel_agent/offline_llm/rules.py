"""Luật đọc ý định từ câu tiếng Việt — chỉ dùng cho model offline (không có API key).

Khi có OPENAI_API_KEY, việc hiểu câu do gpt-5-mini làm; file này chỉ để demo và test chạy được.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from excel_agent.core.text import find_name, normalize

Intent = Literal["append", "update", "find_sheet", "report", "search", "help"]
CODE = re.compile(r"\b(?:KH|SP|DH|ĐH)-\d+\b", re.IGNORECASE)
SHEET_TAIL = re.compile(r"\s+(?:trong|vào|ở)\s+(?:bảng|sheet|file|excel)\b.*$", re.IGNORECASE)
QUOTED = re.compile(r"[\"“'‘]([^\"”'’]+)[\"”'’]")

CITIES = {
    "ha noi": "Hà Nội",
    "tp ho chi minh": "TP. Hồ Chí Minh",
    "tp. ho chi minh": "TP. Hồ Chí Minh",
    "ho chi minh": "TP. Hồ Chí Minh",
    "sai gon": "TP. Hồ Chí Minh",
    "hcm": "TP. Hồ Chí Minh",
    "da nang": "Đà Nẵng",
    "hai phong": "Hải Phòng",
    "can tho": "Cần Thơ",
    "nha trang": "Nha Trang",
    "hue": "Huế",
    "bac ninh": "Bắc Ninh",
}
SEGMENTS = {"doanh nghiep": "Doanh nghiệp", "dai ly": "Đại lý", "ca nhan": "Cá nhân"}
ORDER_STATUS = {"dang giao": "Đang giao", "da giao": "Đã giao", "da huy": "Đã hủy"}
SEARCH_WORDS = ("/search", "tim ", "tim kiem", "tra cuu", "search", "kiem tra")
REPORT_WORDS = ("excel", "xuat", "tao file", "lap file", "bao cao", "danh sach", "file")
APPEND_WORDS = ("them", "chen", "bo sung", "dua")
UPDATE_WORDS = ("ghi", "dien", "cap nhat", "sua", "doi")
SHEET_WORDS = (
    "vao bang",
    "trong bang",
    "vao sheet",
    "trong sheet",
    "vao excel",
    "trong excel",
    "trong file",
    "vao file",
)
# Từ bỏ đi khi rút từ khóa tìm kiếm khỏi câu tự nhiên (đã chuẩn hóa, không dấu)
_STOP = "tim kiem tra cuu search giup toi minh cho cac nhung khach hang san pham don o tai thuoc co la voi ten trong"
STOP_WORDS = frozenset(_STOP.split()) | {
    "du",
    "lieu",
    "he",
    "thong",
    "dong",
    "bang",
    "sheet",
    "file",
    "excel",
    "dang",
    "mo",
}


def _padded(text: str) -> str:
    return f" {normalize(text)} "


def detect_intent(text: str) -> Intent:
    n = _padded(text)
    in_sheet = any(f" {w} " in n for w in SHEET_WORDS)
    if in_sheet and any(f" {w} " in n for w in APPEND_WORDS):
        return "append"
    if QUOTED.search(text) and " cot " in n and any(f" {w} " in n for w in UPDATE_WORDS):
        return "update"
    if in_sheet and any(f" {w.strip()} " in n for w in SEARCH_WORDS):
        return "find_sheet"
    if n.strip().startswith("/search") or any(f" {w.strip()} " in n for w in SEARCH_WORDS):
        return "search"
    if any(f" {w} " in n for w in REPORT_WORDS):
        return "report"
    return "help"


def detect_dataset(text: str) -> str | None:
    n = _padded(text)
    if " don hang " in n or " don " in n:
        return "don_hang"
    if " san pham " in n or " hang hoa " in n or " mat hang " in n:
        return "san_pham"
    if " khach " in n:
        return "khach_hang"
    return None


def report_args(text: str) -> dict[str, Any]:
    dataset = detect_dataset(text) or "khach_hang"
    n = _padded(text)
    filters: list[dict[str, str]] = []
    if dataset == "khach_hang":
        city = next((v for k, v in CITIES.items() if f" {k} " in n), None)
        if city:
            filters.append({"column": "Thành phố", "op": "eq", "value": city})
        segment = next((v for k, v in SEGMENTS.items() if f" {k} " in n), None)
        if segment:
            filters.append({"column": "Phân khúc", "op": "eq", "value": segment})
    if dataset == "don_hang":
        status = next((v for k, v in ORDER_STATUS.items() if f" {k} " in n), None)
        if status:
            filters.append({"column": "Trạng thái", "op": "eq", "value": status})
    return {"dataset": dataset, "filters": filters, "columns": None, "title": None}


def search_args(text: str) -> dict[str, Any]:
    words = [w for w in text.replace("/search", " ").split() if normalize(w) not in STOP_WORDS]
    return {"query": " ".join(words).strip(), "column": None, "dataset": detect_dataset(text)}


def record_query(text: str) -> dict[str, Any]:
    """ "Thêm khách hàng KH-0012 vào bảng" → tìm KH-0012 trong hệ thống."""
    code = CODE.search(text)
    if code:
        return {"query": code.group(0).upper(), "column": None, "dataset": detect_dataset(text)}
    words = [w for w in text.split() if normalize(w) not in STOP_WORDS | {"them", "chen", "bo", "sung", "dua", "vao"}]
    return {"query": " ".join(words).strip(), "column": None, "dataset": detect_dataset(text)}


def sheet_find_args(text: str, headers: list[str]) -> dict[str, Any]:
    """ "Tìm dòng có Thành phố là Đà Nẵng trong bảng" → excel_find_rows(column="Thành phố", query="Đà Nẵng")."""
    n = _padded(text)
    column = next((h for h in sorted(headers, key=len, reverse=True) if f" {normalize(h)} " in n), None)
    rest = text
    if column:
        rest = re.sub(re.escape(column), " ", rest, flags=re.IGNORECASE)
    value = re.search(r"\s(?:là|bằng|=)\s+(.+)", rest, flags=re.IGNORECASE)
    if value:  # "… Trạng thái là Đang giao trong bảng" → lấy nguyên giá trị sau "là"
        query = SHEET_TAIL.split(value.group(1))[0]
    else:
        query = " ".join(w for w in rest.split() if normalize(w) not in STOP_WORDS | {"vao", "o", "cot"})
    return {"query": query.strip(" .?"), "column": column, "match": "contains", "limit": 20}


def update_args(text: str, headers: list[str], rows: list[int]) -> dict[str, Any] | None:
    """ "Ghi 'VIP' vào cột Phân khúc cho các dòng đang chọn" → excel_set_values."""
    value = QUOTED.search(text)
    n = _padded(text)
    after = n.split(" cot ", 1)[1] if " cot " in n else ""
    column = next((h for h in sorted(headers, key=len, reverse=True) if after.startswith(f"{normalize(h)} ")), None)
    if not value or not column:
        return None
    return {"column": column, "rows": rows, "values": [value.group(1)], "create_column": False}


def map_record(record: dict[str, Any], headers: list[str]) -> dict[str, Any]:
    """Bản ghi hệ thống → một dòng theo tên cột của sheet (chỉ cột khớp tên)."""
    row: dict[str, Any] = {}
    for header in headers:
        field = find_name(list(record), header)
        if field is not None:
            row[header] = record[field]
    return row
