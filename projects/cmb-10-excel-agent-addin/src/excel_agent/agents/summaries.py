"""Câu trả lời ngắn từ kết quả tool — dùng cho lệnh `/` và model offline (không gọi LLM)."""

from __future__ import annotations

import json
from typing import Any

HELP_TEXT = (
    "Mình có thể:\n"
    "- **Xuất file Excel** từ hệ thống: *Tạo file Excel khách hàng ở Hà Nội* rồi bấm vào thẻ file để xem dữ liệu.\n"
    "- **Tìm trong sheet đang mở**: *Tìm dòng có Thành phố là Đà Nẵng trong bảng*.\n"
    "- **Lấy bản ghi từ hệ thống đưa vào sheet**: *Thêm khách hàng KH-0012 vào bảng* — xem trước, bấm xác nhận "
    "mới ghi.\n"
    '- **Ghi vào cột cho các dòng đang chọn**: *Ghi "VIP" vào cột Phân khúc cho các dòng đang chọn*.\n'
    "- **Lệnh nhanh, không tốn token**: `/search Đà Nẵng` (tìm trong hệ thống theo cột đang chọn hoặc mọi cột), "
    "`/search Thành phố: Đà Nẵng`, `/search in:san_pham laptop`, `/datasets`, `/help`. "
    "Tích chọn kết quả rồi bấm **Ghi vào cột** hoặc **Thêm thành dòng mới**."
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


def _rows(rows: list[int]) -> str:
    shown = ", ".join(str(r) for r in rows[:10])
    return shown + ("…" if len(rows) > 10 else "")


def summarize_excel(tool: str, raw: str) -> str:
    """Câu trả lời từ kết quả của công cụ Excel (chạy trong add-in) — dùng cho model offline."""
    try:
        data: dict[str, Any] = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return str(raw)
    status = data.get("status")
    if status == "rejected":
        return "Bạn đã hủy nên mình chưa ghi gì vào sheet."
    if status == "error":
        return f"Không ghi được: {data.get('message')}"
    if tool == "excel_find_rows":
        matches = data.get("matches") or []
        scope = f" trong cột {data['column']}" if data.get("column") else ""
        if not matches:
            return f"Không có dòng nào chứa “{data.get('query')}”{scope} trong sheet {data.get('sheet')}."
        return (
            f"Có {data.get('total', len(matches))} dòng chứa “{data.get('query')}”{scope} trong sheet "
            f"{data.get('sheet')}: dòng {_rows([m['row'] for m in matches])}. Mình đã chọn dòng tìm được trên sheet."
        )
    if tool == "excel_append_rows":
        return f"Đã thêm {data.get('rows_added', 0)} dòng vào sheet {data.get('sheet')} (dòng {data.get('first_row')})."
    if tool == "excel_set_values":
        return (
            f"Đã ghi vào cột {data.get('column')} cho {len(data.get('changed_rows') or [])} dòng: "
            f"{_rows(data.get('changed_rows') or [])}."
        )
    return data.get("message") or str(raw)
