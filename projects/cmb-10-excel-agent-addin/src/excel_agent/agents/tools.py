"""Tool của agent (OpenAI Agents SDK).

Mỗi tool có hai lớp: hàm `run_*` thuần (dùng chung cho lệnh `/search` không qua LLM và cho test) và
wrapper `@function_tool` cho agent. Kết quả trả về là JSON có trường `type` để giao diện vẽ thẻ tương
ứng: `workbook` (thẻ file Excel), `search_results` (bảng kết quả chọn được), `datasets`, `error`.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Literal

from agents import RunContextWrapper, function_tool
from pydantic import BaseModel

from excel_agent.agents.context import AgentDeps
from excel_agent.core.exceptions import ExcelAgentError
from excel_agent.core.text import find_name
from excel_agent.schemas.data_api import ExportRequest, Filter


class FilterArg(BaseModel):
    """Một điều kiện lọc. Mọi trường bắt buộc để schema hợp lệ ở strict mode."""

    column: str
    op: Literal["eq", "contains", "gt", "gte", "lt", "lte"]
    value: str


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _error(message: str) -> str:
    return _json({"type": "error", "message": message})


async def run_list_datasets(deps: AgentDeps) -> str:
    try:
        datasets = await deps.datasets()
    except ExcelAgentError as exc:
        return _error(str(exc))
    return _json(
        {
            "type": "datasets",
            "datasets": [
                {
                    "name": d["name"],
                    "title": d["title"],
                    "rows": d["rows"],
                    "columns": [c["name"] for c in d["columns"]],
                }
                for d in datasets
            ],
        }
    )


async def run_export_excel(
    deps: AgentDeps,
    dataset: str,
    filters: list[FilterArg] | None = None,
    columns: list[str] | None = None,
    title: str | None = None,
) -> str:
    req = ExportRequest(
        dataset=dataset,
        filters=[Filter(column=f.column, op=f.op, value=f.value) for f in filters or []],
        columns=columns or None,
        title=title or None,
    )
    try:
        content, filename, rows = await deps.data_api.export(req)
        source = {"dataset": dataset, "filters": [f.model_dump() for f in req.filters], "api": "/export"}
        info = await asyncio.to_thread(deps.workbooks.create, content, filename, source)
    except ExcelAgentError as exc:
        return _error(str(exc))
    return _json(
        {
            "type": "workbook",
            "workbook_id": info.id,
            "name": info.name,
            "dataset": dataset,
            "filters": source["filters"],
            "rows": rows,
            "columns": info.columns,
            "sheets": info.sheets,
            "preview_url": info.preview_url,
            "download_url": info.download_url,
        }
    )


async def run_search_data(
    deps: AgentDeps,
    query: str,
    column: str | None = None,
    dataset: str | None = None,
    limit: int | None = None,
) -> str:
    dataset = dataset or deps.active_dataset() or deps.settings.default_dataset
    limit = min(limit or deps.settings.max_tool_rows, deps.settings.max_tool_rows)
    try:
        if not column and deps.ui.selected_column:
            # "search theo cột đó": giao diện đang chọn cột nào thì tìm trong cột đó nếu dataset có cột này
            info = next((d for d in await deps.datasets() if d["name"] == dataset), None)
            if info and find_name([c["name"] for c in info["columns"]], deps.ui.selected_column):
                column = deps.ui.selected_column
        result = await deps.data_api.search(query, dataset, column, limit)
    except ExcelAgentError as exc:
        return _error(str(exc))
    return _json(
        {
            "type": "search_results",
            "dataset": result.dataset,
            "query": result.query,
            "column": result.column,
            "total": result.total,
            "shown": len(result.records),
            "columns": result.columns,
            "records": result.records,
            "target": {
                "workbook_id": deps.ui.active_workbook_id,
                "column": deps.ui.selected_column,
                "rows": deps.ui.selected_rows,
            },
        }
    )


@function_tool
async def list_datasets(ctx: RunContextWrapper[AgentDeps]) -> str:
    """Liệt kê các dataset của API dữ liệu và tên cột của từng dataset."""
    return await run_list_datasets(ctx.context)


@function_tool
async def export_excel(
    ctx: RunContextWrapper[AgentDeps],
    dataset: str,
    filters: list[FilterArg],
    columns: list[str] | None = None,
    title: str | None = None,
) -> str:
    """Gọi API dữ liệu để xuất dữ liệu thành file Excel; giao diện hiện thẻ file để người dùng bấm xem.

    Args:
        dataset: Tên dataset: khach_hang, san_pham hoặc don_hang.
        filters: Bộ lọc theo cột; danh sách rỗng nếu lấy toàn bộ.
        columns: Chỉ lấy các cột này; bỏ trống để lấy mọi cột.
        title: Tên sheet của file; bỏ trống để dùng tên dataset.
    """
    return await run_export_excel(ctx.context, dataset, filters, columns, title)


@function_tool
async def search_data(
    ctx: RunContextWrapper[AgentDeps],
    query: str,
    column: str | None = None,
    dataset: str | None = None,
) -> str:
    """Tìm bản ghi qua API search; giao diện hiện bảng kết quả để người dùng chọn và áp vào cột Excel.

    Args:
        query: Từ khóa cần tìm (không phân biệt dấu, hoa thường).
        column: Chỉ tìm trong cột này; bỏ trống để tìm mọi cột.
        dataset: khach_hang, san_pham hoặc don_hang; bỏ trống để dùng dataset của file đang mở.
    """
    return await run_search_data(ctx.context, query, column, dataset)
