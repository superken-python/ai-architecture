"""Ngữ cảnh chạy của agent: service dùng chung + trạng thái Excel mà add-in gửi lên qua AG-UI `context`.

Giao diện (web POC hoặc task pane trong Excel) gửi mỗi lượt một mục context `{"description": "excel_ui",
"value": "<JSON>"}`. Agno đưa nó vào `run_context.dependencies["excel_ui"]` (và vào cuối câu hỏi gửi model),
tool phía server đọc lại qua `UiState.from_context`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from excel_agent.core.config import Settings
from excel_agent.core.text import normalize
from excel_agent.services.data_api_client import DataApiClient
from excel_agent.services.workbook_service import WorkbookService

UI_CONTEXT_KEY = "excel_ui"  # `description` của mục context AG-UI mà giao diện gửi lên


def _ints(values: Any) -> list[int]:
    return [int(v) for v in values or [] if isinstance(v, int | float | str) and str(v).isdigit()]


@dataclass
class UiState:
    """Workbook/sheet đang mở và vùng đang chọn. Số dòng là số dòng thật trong Excel (dòng tiêu đề = 1)."""

    host: str = "web"  # web (POC) | office (add-in trong Excel)
    workbook_id: str | None = None  # chỉ có ở web POC (file lưu trên server)
    workbook: str | None = None
    sheet: str | None = None
    headers: list[str] = field(default_factory=list)
    selected_column: str | None = None
    selected_rows: list[int] = field(default_factory=list)

    @classmethod
    def from_context(cls, raw: Any) -> UiState:
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                return cls()
        if not isinstance(raw, dict):
            return cls()
        selection = raw.get("selection") if isinstance(raw.get("selection"), dict) else {}
        return cls(
            host=str(raw.get("host") or "web"),
            workbook_id=raw.get("workbook_id") or None,
            workbook=raw.get("workbook") or None,
            sheet=raw.get("sheet") or None,
            headers=[str(h) for h in raw.get("headers") or [] if h not in (None, "")],
            selected_column=selection.get("column") or None,
            selected_rows=_ints(selection.get("rows")),
        )


@dataclass
class AgentDeps:
    """Service dùng chung + trạng thái giao diện của lượt chạy hiện tại."""

    settings: Settings
    data_api: DataApiClient
    workbooks: WorkbookService
    ui: UiState = field(default_factory=UiState)
    _datasets: list[dict[str, Any]] | None = None

    async def datasets(self) -> list[dict[str, Any]]:
        if self._datasets is None:
            self._datasets = [d.model_dump() for d in await self.data_api.list_datasets()]
        return self._datasets

    async def active_dataset(self) -> str | None:
        """Dataset ứng với sheet đang mở: theo nguồn của file (web POC) hoặc theo tên cột (Excel thật)."""
        if self.ui.workbook_id:
            try:
                dataset = self.workbooks.info(self.ui.workbook_id).source.get("dataset")
            except Exception:  # file đã bị xóa hoặc mã sai → đoán theo tên cột
                dataset = None
            if dataset:
                return dataset
        if not self.ui.headers:
            return None
        headers = {normalize(h) for h in self.ui.headers}
        best, score = None, 0.0
        for d in await self.datasets():
            columns = {normalize(c["name"]) for c in d["columns"]}
            overlap = len(headers & columns) / max(len(columns), 1)
            if overlap > score:
                best, score = d["name"], overlap
        return best if score >= 0.5 else None


DepsFactory = Callable[[UiState], AgentDeps]
