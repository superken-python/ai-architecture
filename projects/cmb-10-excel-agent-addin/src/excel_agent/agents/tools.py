"""Tool phía server của agent (gọi API hệ thống) — chạy trong AgentOS.

Tool phía Excel (`excel_*`: đọc sheet, tìm dòng, ghi ô, thêm dòng) KHÔNG nằm ở đây: add-in khai báo chúng
trong `RunAgentInput.tools` mỗi lượt, AgentOS biến thành tool `external_execution` → run tạm dừng, add-in chạy
bằng Office.js rồi gửi kết quả về để run chạy tiếp. Danh sách tool đó: `web/js/excel-tools.js`.

Mỗi tool ở đây có hai lớp: hàm `run_*` thuần (dùng chung cho lệnh `/search` không qua LLM và cho test) và
method của `SystemDataTools` cho agent. Kết quả là JSON có trường `type` để giao diện vẽ thẻ tương ứng:
`workbook` (thẻ file Excel), `search_results` (bảng kết quả chọn được), `datasets`, `error`.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Literal

from agno.run.base import RunContext
from agno.tools import Toolkit
from pydantic import BaseModel

from excel_agent.agents.context import UI_CONTEXT_KEY, AgentDeps, DepsFactory, UiState
from excel_agent.core.exceptions import ExcelAgentError
from excel_agent.core.text import find_name
from excel_agent.schemas.data_api import ExportRequest, Filter


class FilterArg(BaseModel):
    """Một điều kiện lọc."""

    column: str
    op: Literal["eq", "contains", "gt", "gte", "lt", "lte"] = "eq"
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
    use_selected_column: bool = False,
) -> str:
    """`use_selected_column` chỉ bật cho lệnh `/search` (người dùng chủ động chọn cột trên sheet); agent tự chọn cột."""
    limit = min(limit or deps.settings.max_tool_rows, deps.settings.max_tool_rows)
    try:
        dataset = dataset or await deps.active_dataset() or deps.settings.default_dataset
        if use_selected_column and not column and deps.ui.selected_column:
            # "/search theo cột đó": đang chọn cột nào trong Excel thì tìm trong cột đó nếu dataset có cột này
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
        }
    )


class SystemDataTools(Toolkit):
    """Công cụ gọi API dữ liệu của hệ thống (ERP/CRM giả lập trong POC)."""

    def __init__(self, deps_factory: DepsFactory) -> None:
        self._deps_factory = deps_factory
        super().__init__(name="system_data", tools=[self.list_datasets, self.search_data, self.export_excel])

    def _deps(self, run_context: RunContext | None) -> AgentDeps:
        dependencies = (run_context.dependencies if run_context else None) or {}
        return self._deps_factory(UiState.from_context(dependencies.get(UI_CONTEXT_KEY)))

    async def list_datasets(self, run_context: RunContext) -> str:
        """Liệt kê các dataset của hệ thống và tên cột của từng dataset."""
        return await run_list_datasets(self._deps(run_context))

    async def search_data(
        self, run_context: RunContext, query: str, column: str | None = None, dataset: str | None = None
    ) -> str:
        """Tìm bản ghi trong HỆ THỐNG (API dữ liệu, không phải sheet đang mở). Giao diện hiện bảng kết quả
        để người dùng chọn; muốn đưa bản ghi vào sheet thì gọi tiếp excel_append_rows hoặc excel_set_values.

        Args:
            query: Từ khóa cần tìm (không phân biệt dấu, hoa thường), ví dụ mã KH-0012 hoặc "Đà Nẵng".
            column: Chỉ tìm trong cột này của dataset; bỏ trống để tìm mọi cột.
            dataset: khach_hang, san_pham hoặc don_hang; bỏ trống để dùng dataset khớp với sheet đang mở.
        """
        return await run_search_data(self._deps(run_context), query, column, dataset)

    async def export_excel(
        self,
        run_context: RunContext,
        dataset: str,
        filters: list[FilterArg] | None = None,
        columns: list[str] | None = None,
        title: str | None = None,
    ) -> str:
        """Gọi API hệ thống để xuất dữ liệu thành một FILE EXCEL MỚI; giao diện hiện thẻ file để người dùng
        bấm xem (hoặc chèn vào workbook đang mở khi chạy trong Excel).

        Args:
            dataset: Tên dataset: khach_hang, san_pham hoặc don_hang.
            filters: Bộ lọc theo cột, mỗi phần tử {column, op, value}; op là eq, contains, gt, gte, lt, lte.
            columns: Chỉ lấy các cột này; bỏ trống để lấy mọi cột.
            title: Tên sheet của file; bỏ trống để dùng tên dataset.
        """
        return await run_export_excel(self._deps(run_context), dataset, filters, columns, title)
