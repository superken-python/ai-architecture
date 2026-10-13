"""Giao kèo của API dữ liệu (giả lập ERP/CRM): danh mục dataset, xuất Excel, tìm kiếm."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ColumnType = Literal["text", "number", "money", "date"]
FilterOp = Literal["eq", "contains", "gt", "gte", "lt", "lte"]


class ColumnInfo(BaseModel):
    name: str
    type: ColumnType = "text"


class DatasetInfo(BaseModel):
    name: str
    title: str
    key: str
    columns: list[ColumnInfo]
    rows: int = 0


class Filter(BaseModel):
    column: str = Field(description="Tên cột, ví dụ 'Thành phố'")
    op: FilterOp = Field(default="eq", description="eq | contains | gt | gte | lt | lte")
    value: str = Field(description="Giá trị so sánh, dạng chữ")


class ExportRequest(BaseModel):
    dataset: str
    filters: list[Filter] = Field(default_factory=list)
    columns: list[str] | None = None
    title: str | None = None
    limit: int = Field(default=1000, ge=1, le=5000)


class SearchResponse(BaseModel):
    dataset: str
    query: str
    column: str | None = None
    total: int
    columns: list[str]
    records: list[dict[str, Any]]
