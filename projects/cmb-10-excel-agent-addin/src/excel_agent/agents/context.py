"""Ngữ cảnh chạy của agent: service dùng chung + trạng thái giao diện Excel gửi lên qua AG-UI."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from excel_agent.core.config import Settings
from excel_agent.services.data_api_client import DataApiClient
from excel_agent.services.workbook_service import WorkbookService

UI_CONTEXT_KEY = "excel_ui"  # `description` của mục context AG-UI mà giao diện gửi lên


@dataclass
class UiState:
    """Những gì người dùng đang mở/chọn trên giao diện (file, sheet, cột, dòng)."""

    active_workbook_id: str | None = None
    sheet: str | None = None
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
        rows = raw.get("selected_rows") or []
        return cls(
            active_workbook_id=raw.get("active_workbook_id") or None,
            sheet=raw.get("sheet") or None,
            selected_column=raw.get("selected_column") or None,
            selected_rows=[int(r) for r in rows if isinstance(r, int | float | str) and str(r).isdigit()],
        )


@dataclass
class AgentDeps:
    """Truyền vào `Runner.run(context=...)`; tool đọc qua `RunContextWrapper[AgentDeps]`."""

    settings: Settings
    data_api: DataApiClient
    workbooks: WorkbookService
    ui: UiState = field(default_factory=UiState)
    _datasets: list[dict[str, Any]] | None = None

    async def datasets(self) -> list[dict[str, Any]]:
        if self._datasets is None:
            self._datasets = [d.model_dump() for d in await self.data_api.list_datasets()]
        return self._datasets

    def active_dataset(self) -> str | None:
        """Dataset của file Excel đang mở (nếu file do export_excel tạo)."""
        if not self.ui.active_workbook_id:
            return None
        try:
            return self.workbooks.info(self.ui.active_workbook_id).source.get("dataset")
        except Exception:  # file đã bị xóa hoặc mã sai → coi như không có
            return None

    def describe_ui(self) -> str:
        if not self.ui.active_workbook_id:
            return "chưa mở file Excel nào"
        parts = [f"đang mở workbook {self.ui.active_workbook_id}"]
        dataset = self.active_dataset()
        if dataset:
            parts.append(f"dataset {dataset}")
        if self.ui.selected_column:
            parts.append(f"đang chọn cột '{self.ui.selected_column}'")
        if self.ui.selected_rows:
            parts.append(f"đang chọn {len(self.ui.selected_rows)} dòng")
        return ", ".join(parts)
