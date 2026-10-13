"""Luật đọc ý định từ câu tiếng Việt — chỉ dùng cho model offline (không có API key) và lệnh `/`.

Khi có OPENAI_API_KEY, việc hiểu câu do gpt-5-mini làm; file này chỉ để demo và test chạy được.
"""

from __future__ import annotations

from typing import Any, Literal

from excel_agent.core.text import normalize

Intent = Literal["report", "search", "help"]

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
# Từ bỏ đi khi rút từ khóa tìm kiếm khỏi câu tự nhiên (đã chuẩn hóa, không dấu)
_STOP = "tim kiem tra cuu search giup toi minh cho cac nhung khach hang san pham don o tai thuoc co la voi ten trong"
STOP_WORDS = frozenset(_STOP.split()) | {"du", "lieu", "he", "thong"}


def _padded(text: str) -> str:
    return f" {normalize(text)} "


def detect_intent(text: str) -> Intent:
    n = _padded(text)
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
