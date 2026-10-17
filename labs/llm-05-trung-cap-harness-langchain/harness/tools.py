"""Tool của agent.

- Tool server: chạy trong tiến trình agent (tương đương tool trong `tools=[...]` của Agno).
- Tool client (frontend tool): agent chỉ khai báo; thân tool gọi `interrupt()` để dừng run, client (add-in Excel)
  chạy thật rồi gửi kết quả về bằng `Command(resume=...)`. Tương đương `external_execution=True` của Agno.

Lưu ý khi resume: LangGraph chạy lại thân tool client từ đầu tới `interrupt()` (tool server chạy song song thì
không chạy lại). Vì vậy không đặt side effect trước `interrupt()`.
"""

from __future__ import annotations

import json
from typing import Any

from langchain.tools import BaseTool, ToolRuntime, tool
from langgraph.types import interrupt

from harness.data import FIELDS, CustomerDB


def make_server_tools(db: CustomerDB) -> list[BaseTool]:
    @tool
    def search_customers(query: str) -> str:
        """Tìm khách hàng theo mã (KH-0012), tên hoặc thành phố.

        Dùng khi người dùng hỏi về một khách hàng hoặc một nhóm khách hàng cụ thể.
        Không dùng khi câu hỏi đã có đủ dữ liệu trong lịch sử hội thoại.
        """
        rows = db.search(query)
        if not rows:
            return f"Không thấy khách hàng khớp '{query}'. Thử mã dạng KH-0012, một phần tên, hoặc tên thành phố."
        return json.dumps(rows, ensure_ascii=False)

    @tool
    def update_customer(customer_id: str, field: str, value: str) -> str:
        """Cập nhật MỘT trường của MỘT khách hàng trong hệ thống.

        Chỉ dùng sau khi đã tìm thấy đúng khách hàng bằng search_customers.
        field là một trong: name, city, credit_limit, debt, status.
        """
        try:
            db.update(customer_id, field, value)
        except KeyError as exc:
            fields = ", ".join(FIELDS)
            return f"Không cập nhật được: {exc}. Trường hợp lệ: {fields}. Kiểm tra lại mã bằng search_customers."
        return f"Đã cập nhật {customer_id}.{field} = {value}"

    return [search_customers, update_customer]


def _client_call(runtime: ToolRuntime, name: str, args: dict[str, Any]) -> str:
    """Dừng run, chờ client chạy tool. Giá trị resume được trả về cho model như kết quả tool."""
    result = interrupt({"type": "client_tool", "name": name, "args": args, "tool_call_id": runtime.tool_call_id})
    return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)


@tool
def excel_read_rows(rows: list[int], runtime: ToolRuntime) -> str:
    """Đọc các dòng (số dòng Excel, bắt đầu từ 2) trên sheet đang mở. Chạy trong add-in."""
    return _client_call(runtime, "excel_read_rows", {"rows": rows})


@tool
def excel_set_values(cells: dict[str, str], runtime: ToolRuntime) -> str:
    """Ghi giá trị vào ô trên sheet đang mở, ví dụ {"E2": "Hoàn tất"}. Chạy trong add-in, người dùng xác nhận trước."""
    return _client_call(runtime, "excel_set_values", {"cells": cells})


CLIENT_TOOLS: list[BaseTool] = [excel_read_rows, excel_set_values]
