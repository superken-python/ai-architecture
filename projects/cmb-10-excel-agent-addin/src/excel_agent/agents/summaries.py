"""Câu trả lời ngắn từ kết quả tool — dùng cho lệnh `/` và model offline (không gọi LLM)."""

from __future__ import annotations

import json
from typing import Any

HELP_TEXT = (
    "Mình có thể:\n"
    "- **Xuất file Excel** từ hệ thống: gõ ví dụ *Tạo file Excel khách hàng ở Hà Nội* rồi bấm vào thẻ file "
    "để xem dữ liệu.\n"
    "- **Tìm dữ liệu rồi áp vào bảng**: `/search Đà Nẵng` (tìm mọi cột), "
    "`/search Thành phố: Đà Nẵng` (tìm theo cột), "
    "`/search in:san_pham laptop` (chọn dataset). "
    "Nếu đang chọn một cột trên bảng Excel, `/search` sẽ tìm theo cột đó.\n"
    "- Tích chọn kết quả rồi bấm **Ghi vào cột** (ghi vào các dòng đang chọn) hoặc **Thêm thành dòng mới**.\n"
    "- `/datasets` xem danh sách dữ liệu, `/help` xem hướng dẫn này."
)


def summarize(raw: str) -> str:
    try:
        data: dict[str, Any] = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return str(raw)
    kind = data.get("type")
    if kind == "workbook":
        filters = "; ".join(f"{f['column']} {f['op']} {f['value']}" for f in data.get("filters", []))
        where = f", lọc {filters}" if filters else ""
        return (
            f"Đã tạo file **{data['name']}** gồm {data['rows']} dòng, {len(data.get('columns', []))} cột "
            f"(dataset {data.get('dataset')}{where}). Bấm vào thẻ file để xem dữ liệu."
        )
    if kind == "search_results":
        scope = f" trong cột {data['column']}" if data.get("column") else ""
        shown = f", hiển thị {data['shown']}" if data.get("shown", 0) < data.get("total", 0) else ""
        if not data.get("total"):
            return f"Không tìm thấy kết quả cho “{data.get('query')}”{scope} trong {data.get('dataset')}."
        return (
            f"Tìm thấy {data['total']} kết quả cho “{data.get('query')}”{scope} ({data.get('dataset')}{shown}). "
            "Tích chọn kết quả rồi bấm **Ghi vào cột** hoặc **Thêm thành dòng mới**."
        )
    if kind == "datasets":
        lines = [f"- `{d['name']}` · {d['title']} · {d['rows']} dòng" for d in data.get("datasets", [])]
        return "Dữ liệu có sẵn:\n" + "\n".join(lines)
    if kind == "error":
        return f"Không thực hiện được: {data.get('message')}"
    return str(raw)
