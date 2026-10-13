"""Agent với model "kịch bản" — mô phỏng gpt-5-mini gọi tool (server + Excel), đi qua đúng đường code thật:
AG-UI → AgentOS → Agno Agent → OpenAIResponses(id="gpt-5-mini") → SDK openai → API Responses giả lập.

Không cần API key; `ScriptBrain` trả lần lượt các bước đã định và lưu request để kiểm tra model đã nhận gì.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from agno.models.openai import OpenAIResponses

from excel_agent.core.config import Settings
from excel_agent.offline_llm.app import BASE_URL, Call, Text, http_client
from excel_agent.offline_llm.brains import ScriptBrain
from tests.conftest import EXCEL_TOOLS, SHEET_UI, agui_resume, agui_run, pending_calls, text_of, tool_results


def _items(request: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [i for i in request["input"] if isinstance(i, dict) and i.get("type") == kind]


@pytest.fixture
def brain() -> ScriptBrain:
    return ScriptBrain([])


@pytest.fixture
async def scripted(
    settings: Settings, mock_http: httpx.AsyncClient, brain: ScriptBrain
) -> AsyncIterator[httpx.AsyncClient]:
    from excel_agent.main import create_app

    model = OpenAIResponses(
        id="gpt-5-mini",
        api_key="test",
        base_url=BASE_URL,
        http_client=http_client(brain),
        reasoning_effort="low",
        store=False,
    )
    app = create_app(settings, data_api_http=mock_http, model=model)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", timeout=60) as c:
        yield c


async def test_model_driven_export_with_numeric_filter(scripted: httpx.AsyncClient, brain: ScriptBrain) -> None:
    args = {
        "dataset": "khach_hang",
        "filters": [{"column": "Hạn mức nợ (VND)", "op": "gte", "value": "200000000"}],
        "columns": ["Mã KH", "Tên khách hàng", "Hạn mức nợ (VND)"],
        "title": "KH hạn mức lớn",
    }
    brain.steps = [[Call("export_excel", args)], [Text("Đã tạo file khách hàng hạn mức lớn.")]]
    events = await agui_run(scripted, "xuất khách hàng có hạn mức từ 200 triệu", tools=EXCEL_TOOLS)
    result = tool_results(events)[0]
    assert result["type"] == "workbook" and result["columns"] == args["columns"] and result["rows"] > 0
    assert text_of(events) == "Đã tạo file khách hàng hạn mức lớn."
    brain.assert_complete()

    first = brain.requests[0]
    # model nhận đủ tool server + tool Excel do giao diện khai báo; gpt-5-mini: reasoning low, không lưu ở OpenAI
    assert {t["name"] for t in first["tools"]} >= {
        "search_data",
        "export_excel",
        "excel_find_rows",
        "excel_append_rows",
    }
    assert first["model"] == "gpt-5-mini" and first["reasoning"]["effort"] == "low" and first["store"] is False
    assert "reasoning.encrypted_content" in first.get("include", [])
    instructions = json.dumps(first["input"], ensure_ascii=False)
    assert "khach_hang (Khách hàng" in instructions and "excel_ui" in instructions


async def test_search_then_append_with_pause_resume(scripted: httpx.AsyncClient, brain: ScriptBrain) -> None:
    """Model gọi song song search_data (server) + excel_get_context (Excel): server chạy ngay, Excel tạm dừng."""
    row = {"Mã KH": "KH-0007", "Tên khách hàng": "X", "Thành phố": "Huế", "Điện thoại": "0900000007"}
    brain.steps = [
        [Call("search_data", {"query": "KH-0007"}), Call("excel_get_context", {})],
        [Call("excel_append_rows", {"rows": [row]})],
        [Text("Đã thêm KH-0007 vào dòng 12.")],
    ]
    text = "Thêm KH-0007 vào bảng"
    events = await agui_run(scripted, text, thread_id="s-1", ui=SHEET_UI, tools=EXCEL_TOOLS)
    assert tool_results(events)[0]["records"][0]["Mã KH"] == "KH-0007"
    (ctx_call,) = pending_calls(events)
    assert ctx_call["name"] == "excel_get_context"

    context = {"status": "ok", **SHEET_UI}
    events = await agui_resume(scripted, "s-1", text, {ctx_call["id"]: context}, [ctx_call], SHEET_UI, EXCEL_TOOLS)
    (append_call,) = pending_calls(events)
    assert append_call["name"] == "excel_append_rows" and append_call["args"]["rows"] == [row]

    applied = {"status": "applied", "sheet": "Khách hàng", "rows_added": 1, "first_row": 12, "last_row": 12}
    events = await agui_resume(
        scripted, "s-1", text, {append_call["id"]: applied}, [append_call], SHEET_UI, EXCEL_TOOLS
    )
    assert text_of(events) == "Đã thêm KH-0007 vào dòng 12." and not pending_calls(events)
    brain.assert_complete()

    # model nhận kết quả của cả tool server và tool Excel khi run chạy tiếp
    outputs = [json.loads(o["output"]) for o in _items(brain.requests[1], "function_call_output")]
    assert {o.get("type") for o in outputs} == {"search_results", None}
    assert any(o.get("sheet") == "Khách hàng" for o in outputs)
    last = [json.loads(o["output"]) for o in _items(brain.requests[2], "function_call_output")]
    assert any(o.get("status") == "applied" for o in last)


async def test_tool_error_is_returned_to_model(scripted: httpx.AsyncClient, brain: ScriptBrain) -> None:
    brain.steps = [
        [Call("search_data", {"query": "x", "column": "Không có cột", "dataset": "khach_hang"})],
        [Text("Cột không tồn tại, bạn kiểm tra lại tên cột nhé.")],
    ]
    events = await agui_run(scripted, "tìm x", thread_id="s-2")
    assert tool_results(events)[0]["type"] == "error"
    output = _items(brain.requests[1], "function_call_output")[0]["output"]
    assert "không có cột" in output.lower()
