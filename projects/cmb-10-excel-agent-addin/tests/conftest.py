"""Fixture dùng chung: settings offline + API dữ liệu giả lập gọi qua ASGI (không mạng, không API key)."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from excel_agent.core.config import Settings
from excel_agent.mock_data_api.app import create_app as create_mock_api
from excel_agent.mock_data_api.service import DataRepository
from excel_agent.services.workbook_service import WorkbookService


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        storage_dir=tmp_path / "var",
        openai_api_key=None,
        agent_mode="offline",
        data_api_url="http://mock-api",
    )


@pytest.fixture(scope="session")
def repo() -> DataRepository:
    return DataRepository()


@pytest.fixture
def workbooks(tmp_path: Path) -> WorkbookService:
    return WorkbookService(tmp_path / "wb")


@pytest.fixture
async def mock_http() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_mock_api()), base_url="http://mock-api") as c:
        yield c


@pytest.fixture
async def client(settings: Settings, mock_http: httpx.AsyncClient) -> AsyncIterator[httpx.AsyncClient]:
    from excel_agent.main import create_app

    app = create_app(settings, data_api_http=mock_http)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", timeout=60) as c:
        yield c


# Bản rút gọn của web/js/excel-tools.js (đủ tên + tham số chính); test e2e dùng bản thật trong trình duyệt.
EXCEL_TOOLS: list[dict[str, Any]] = [
    {
        "name": "excel_get_context",
        "description": "Đọc trạng thái Excel",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "excel_find_rows",
        "description": "Tìm dòng trong sheet đang mở",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "column": {"type": ["string", "null"]}},
            "required": ["query"],
        },
    },
    {
        "name": "excel_set_values",
        "description": "Ghi giá trị vào một cột",
        "parameters": {
            "type": "object",
            "properties": {
                "column": {"type": "string"},
                "rows": {"type": "array", "items": {"type": "integer"}},
                "values": {"type": "array", "items": {"type": ["string", "number", "null"]}},
            },
            "required": ["column", "rows", "values"],
        },
    },
    {
        "name": "excel_append_rows",
        "description": "Thêm dòng mới",
        "parameters": {
            "type": "object",
            "properties": {"rows": {"type": "array", "items": {"type": "object"}}},
            "required": ["rows"],
        },
    },
]
SHEET_UI: dict[str, Any] = {
    "host": "office",
    "workbook": "Book1.xlsx",
    "sheet": "Khách hàng",
    "headers": ["Mã KH", "Tên khách hàng", "Thành phố", "Điện thoại"],
    "header_row": 1,
    "last_row": 11,
    "selection": {"address": "Khách hàng!C3:C4", "column": "Thành phố", "rows": [3, 4]},
}


def _body(
    thread_id: str, messages: list[dict[str, Any]], ui: dict[str, Any] | None, tools: list[dict[str, Any]] | None
):
    return {
        "threadId": thread_id,
        "runId": str(uuid.uuid4()),
        "state": {},
        "tools": tools or [],
        "forwardedProps": {},
        "context": [{"description": "excel_ui", "value": json.dumps(ui or {}, ensure_ascii=False)}],
        "messages": messages,
    }


async def _post(client: httpx.AsyncClient, body: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    async with client.stream("POST", "/agui", json=body) as resp:
        assert resp.status_code == 200, await resp.aread()
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


async def agui_run(
    client: httpx.AsyncClient,
    text: str,
    thread_id: str = "t-1",
    ui: dict[str, Any] | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Gọi POST /agui đúng định dạng AG-UI và trả về danh sách sự kiện đã giải mã."""
    messages = [{"id": str(uuid.uuid4()), "role": "user", "content": text}]
    return await _post(client, _body(thread_id, messages, ui, tools))


async def agui_resume(
    client: httpx.AsyncClient,
    thread_id: str,
    text: str,
    results: dict[str, dict[str, Any]],
    calls: list[dict[str, Any]],
    ui: dict[str, Any] | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Gửi kết quả tool Excel (tin nhắn role "tool") để run đang tạm dừng chạy tiếp — như web/js/chat.js."""
    tool_calls = [
        {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": json.dumps(c["args"])}}
        for c in calls
    ]
    messages = [
        {"id": str(uuid.uuid4()), "role": "user", "content": text},
        {"id": str(uuid.uuid4()), "role": "assistant", "content": "", "toolCalls": tool_calls},
        *[
            {"id": str(uuid.uuid4()), "role": "tool", "toolCallId": call_id, "content": json.dumps(result)}
            for call_id, result in results.items()
        ],
    ]
    return await _post(client, _body(thread_id, messages, ui, tools))


def pending_calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tool đã bắt đầu nhưng không có TOOL_CALL_RESULT = tool phía client đang chờ (run tạm dừng)."""
    calls: dict[str, dict[str, Any]] = {}
    for e in events:
        if e["type"] == "TOOL_CALL_START":
            calls[e["toolCallId"]] = {"id": e["toolCallId"], "name": e["toolCallName"], "raw": ""}
        elif e["type"] == "TOOL_CALL_ARGS":
            calls[e["toolCallId"]]["raw"] += e["delta"]
    done = {e["toolCallId"] for e in events if e["type"] == "TOOL_CALL_RESULT"}
    return [{**c, "args": json.loads(c["raw"] or "{}")} for k, c in calls.items() if k not in done]


def tool_results(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [json.loads(e["content"]) for e in events if e["type"] == "TOOL_CALL_RESULT"]


def text_of(events: list[dict[str, Any]]) -> str:
    return "".join(e.get("delta", "") for e in events if e["type"] == "TEXT_MESSAGE_CONTENT")
