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


async def agui_run(
    client: httpx.AsyncClient, text: str, thread_id: str = "t-1", ui: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Gọi POST /agui đúng định dạng AG-UI và trả về danh sách sự kiện đã giải mã."""
    body = {
        "threadId": thread_id,
        "runId": str(uuid.uuid4()),
        "state": {},
        "tools": [],
        "forwardedProps": {},
        "context": [{"description": "excel_ui", "value": json.dumps(ui or {})}],
        "messages": [{"id": str(uuid.uuid4()), "role": "user", "content": text}],
    }
    events: list[dict[str, Any]] = []
    async with client.stream("POST", "/agui", json=body) as resp:
        assert resp.status_code == 200
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


def tool_results(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [json.loads(e["content"]) for e in events if e["type"] == "TOOL_CALL_RESULT"]


def text_of(events: list[dict[str, Any]]) -> str:
    return "".join(e.get("delta", "") for e in events if e["type"] == "TEXT_MESSAGE_CONTENT")
