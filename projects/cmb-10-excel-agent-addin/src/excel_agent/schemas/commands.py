"""Giao kèo của lệnh `/` (chạy bằng code, không gọi model)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CommandRequest(BaseModel):
    text: str = Field(description="Nguyên câu lệnh, ví dụ `/search Thành phố: Đà Nẵng`")
    ui: dict[str, Any] = Field(default_factory=dict, description="Trạng thái Excel — cùng định dạng context excel_ui")


class CommandResponse(BaseModel):
    handled: bool
    result: dict[str, Any] | None = None
    text: str = ""
