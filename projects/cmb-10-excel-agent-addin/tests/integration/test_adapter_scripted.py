"""Adapter với model "kịch bản" — mô phỏng đúng kiểu output mà gpt-5-mini trả về (tool call tự do, nhiều bước).

Không cần API key: `ScriptedModel` của OpenAI Agents SDK trả lần lượt các bước đã định.
"""

from __future__ import annotations

import json

import httpx
from agents import Agent
from agents.testing import ScriptedModel, assistant_message, function_call
from agno.os import AgentOS
from agno.os.interfaces.agui import AGUI

from excel_agent.agents.context import AgentDeps, UiState
from excel_agent.agents.runtime.agentos_adapter import OpenAIAgentsAdapter, build_run_config
from excel_agent.agents.tools import export_excel, search_data
from excel_agent.core.config import Settings
from excel_agent.services.data_api_client import DataApiClient
from excel_agent.services.workbook_service import WorkbookService
from tests.conftest import agui_run, text_of, tool_results


def _app(settings: Settings, mock_http: httpx.AsyncClient, model: ScriptedModel) -> httpx.AsyncClient:
    workbooks = WorkbookService(settings.workbooks_dir)
    data_api = DataApiClient("http://mock-api", client=mock_http)
    agent = Agent[AgentDeps](name="Tester", instructions="test", tools=[export_excel, search_data], model=model)
    adapter = OpenAIAgentsAdapter(
        id="scripted",
        name="Scripted",
        starting_agent=agent,
        deps_factory=lambda ui: AgentDeps(
            settings=settings, data_api=data_api, workbooks=workbooks, ui=ui or UiState()
        ),
        run_config=build_run_config("test", tracing_disabled=True),
    )
    app = AgentOS(agents=[adapter], interfaces=[AGUI(agent=adapter)]).get_app()
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", timeout=60)


async def test_model_driven_export_with_numeric_filter(settings: Settings, mock_http: httpx.AsyncClient) -> None:
    args = {
        "dataset": "khach_hang",
        "filters": [{"column": "Hạn mức nợ (VND)", "op": "gte", "value": "200000000"}],
        "columns": ["Mã KH", "Tên khách hàng", "Hạn mức nợ (VND)"],
        "title": "KH hạn mức lớn",
    }
    model = ScriptedModel(
        [
            [function_call("export_excel", args, call_id="c1")],
            [assistant_message("Đã tạo file khách hàng hạn mức lớn.")],
        ]
    )
    async with _app(settings, mock_http, model) as client:
        events = await agui_run(client, "xuất khách hàng có hạn mức từ 200 triệu")
    result = tool_results(events)[0]
    assert result["type"] == "workbook" and result["columns"] == args["columns"] and result["rows"] > 0
    starts = [e for e in events if e["type"] == "TOOL_CALL_START"]
    assert starts[0]["toolCallName"] == "export_excel"
    tool_args = json.loads("".join(e["delta"] for e in events if e["type"] == "TOOL_CALL_ARGS"))
    assert tool_args["filters"][0]["op"] == "gte"
    assert text_of(events) == "Đã tạo file khách hàng hạn mức lớn."
    model.assert_complete()


async def test_tool_error_is_returned_to_model(settings: Settings, mock_http: httpx.AsyncClient) -> None:
    model = ScriptedModel(
        [
            [
                function_call(
                    "search_data", {"query": "x", "column": "Không có cột", "dataset": "khach_hang"}, call_id="c1"
                )
            ],
            [assistant_message("Cột không tồn tại, bạn kiểm tra lại tên cột nhé.")],
        ]
    )
    async with _app(settings, mock_http, model) as client:
        events = await agui_run(client, "tìm x")
    assert tool_results(events)[0]["type"] == "error"
    # model nhận được thông báo lỗi trong output của tool ở lượt gọi thứ hai
    second_input = model.calls[1].input
    assert any("không có cột" in str(item).lower() for item in second_input)
