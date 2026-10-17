"""Ngữ cảnh của mỗi run — tương đương `dependencies` / AG-UI `context` của Agno.

Truyền vào `agent.invoke(..., context=AgentContext(...))`. Middleware và tool đọc qua `runtime.context`.
Không nằm trong state nên không bị lưu vào checkpointer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentContext:
    user_id: str | None = None  # None = chưa đăng nhập → không đọc/ghi memory (Agno dùng "default" chung)
    role: str = "editor"  # "viewer" chỉ được đọc — dùng cho ToolPolicyMiddleware ở phần cải tiến
    sheet: str | None = None
    headers: list[str] = field(default_factory=list)
    selection: str | None = None  # ví dụ "A2:A5"

    def describe(self) -> str:
        if not self.sheet:
            return "(không có workbook đang mở)"
        cols = ", ".join(self.headers) or "(chưa đọc tiêu đề)"
        return f"Sheet: {self.sheet}\nCột: {cols}\nVùng chọn: {self.selection or '(không)'}"
