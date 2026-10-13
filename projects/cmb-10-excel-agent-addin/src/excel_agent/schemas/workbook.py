"""Giao kèo của workbook: thông tin file, xem dữ liệu, áp kết quả tìm kiếm, hoàn tác."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class VersionInfo(BaseModel):
    version: int
    created_at: str
    action: str
    summary: str


class WorkbookInfo(BaseModel):
    id: str
    name: str
    version: int
    sheets: list[str]
    rows: int
    columns: list[str]
    created_at: str
    source: dict[str, Any] = Field(default_factory=dict)
    versions: list[VersionInfo] = Field(default_factory=list)
    preview_url: str
    download_url: str


class PreviewResponse(BaseModel):
    id: str
    name: str
    version: int
    sheet: str
    sheets: list[str]
    columns: list[str]
    rows: list[list[Any]]
    total_rows: int
    offset: int
    limit: int


class ApplyRequest(BaseModel):
    """Áp các bản ghi đã chọn từ kết quả tìm kiếm vào workbook.

    - `set_column`: ghi giá trị trường `source_field` vào cột `target_column` của các dòng `row_indexes`
      (1 bản ghi → cùng giá trị cho mọi dòng; n bản ghi ↔ n dòng theo thứ tự).
    - `append_rows`: thêm mỗi bản ghi thành một dòng mới, trường khớp tên cột (hoặc theo `mapping`).
    """

    mode: Literal["set_column", "append_rows"]
    records: list[dict[str, Any]] = Field(min_length=1)
    sheet: str | None = None
    target_column: str | None = None
    source_field: str | None = None
    row_indexes: list[int] = Field(default_factory=list, description="Chỉ số dòng dữ liệu, bắt đầu từ 0")
    create_column: bool = False
    mapping: dict[str, str] | None = Field(default=None, description="{tên cột trong Excel: tên trường bản ghi}")
    expected_version: int | None = Field(default=None, description="Chặn ghi đè nếu file đã đổi phiên bản")


class ApplyResponse(BaseModel):
    workbook: WorkbookInfo
    changed_rows: list[int]
    changed_column: str | None = None
    message: str
    warnings: list[str] = Field(default_factory=list)
