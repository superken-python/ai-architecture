"""Lệnh bắt đầu bằng `/` — chạy thẳng bằng code, không gọi LLM (EFF-04: code làm được thì không gọi model).

Giao diện gửi lệnh tới `POST /api/v1/commands` thay vì `/agui`, nên không tốn token và không cần API key.

Cú pháp `/search`:
- `/search Đà Nẵng`                   → tìm mọi cột (hoặc cột đang chọn trong Excel)
- `/search Thành phố: Đà Nẵng`        → tìm theo cột (cũng nhận `Thành phố=Đà Nẵng`)
- `/search in:san_pham laptop`        → chọn dataset (cũng nhận `@san_pham`)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from excel_agent.agents.context import AgentDeps
from excel_agent.agents.summaries import HELP_TEXT, summarize
from excel_agent.agents.tools import run_list_datasets, run_search_data
from excel_agent.core.text import find_name, normalize

CommandName = Literal["search", "datasets", "help", "unknown"]
_DATASET_TOKEN = re.compile(r"(?:^|\s)(?:in:|@)(\S+)")


@dataclass
class Command:
    name: CommandName
    query: str = ""
    column: str | None = None
    dataset: str | None = None
    raw: str = ""


def parse_command(text: str) -> Command | None:
    text = (text or "").strip()
    if not text.startswith("/"):
        return None
    head, _, rest = text[1:].partition(" ")
    name = normalize(head)
    if name in ("search", "s", "tim"):
        dataset = None
        match = _DATASET_TOKEN.search(rest)
        if match:
            dataset = match.group(1)
            rest = (rest[: match.start()] + " " + rest[match.end() :]).strip()
        column = None
        for sep in (":", "="):
            left, found, right = rest.partition(sep)
            if found and left.strip() and right.strip():
                column, rest = left.strip(), right.strip()
                break
        return Command("search", query=rest.strip(), column=column, dataset=dataset, raw=text)
    if name in ("datasets", "data", "dulieu"):
        return Command("datasets", raw=text)
    if name in ("help", "?", "huongdan"):
        return Command("help", raw=text)
    return Command("unknown", query=head, raw=text)


@dataclass
class CommandResult:
    result: dict[str, Any] | None  # cùng định dạng kết quả tool (search_results, datasets) để giao diện vẽ thẻ
    text: str


async def run_command(command: Command, deps: AgentDeps) -> CommandResult:
    if command.name == "help":
        return CommandResult(None, HELP_TEXT)
    if command.name == "datasets":
        raw = await run_list_datasets(deps)
        return CommandResult(json.loads(raw), summarize(raw))
    if command.name == "unknown":
        return CommandResult(None, f"Không có lệnh /{command.query}.\n\n{HELP_TEXT}")
    if not command.query:
        return CommandResult(None, "Gõ từ khóa sau /search, ví dụ `/search Đà Nẵng` hoặc `/search Thành phố: Đà Nẵng`.")
    column, query = command.column, command.query
    if column:
        dataset = command.dataset or await deps.active_dataset() or deps.settings.default_dataset
        info = next((d for d in await deps.datasets() if d["name"] == dataset), None)
        if info is None or find_name([c["name"] for c in info["columns"]], column) is None:
            query, column = f"{column}: {query}", None  # phần trước dấu ":" không phải tên cột
    raw = await run_search_data(deps, query, column, command.dataset, use_selected_column=True)
    return CommandResult(json.loads(raw), summarize(raw))
