"""Model giả lập: đọc request Responses API, luật offline chọn bước tiếp theo, SDK `openai` đọc được stream."""

from __future__ import annotations

import json

import pytest
from openai import AsyncOpenAI

from excel_agent.offline_llm.app import BASE_URL, Call, Text, http_client
from excel_agent.offline_llm.brains import RuleBrain, ScriptBrain, read_turn

TOOLS = [{"type": "function", "name": n} for n in ("search_data", "excel_get_context", "excel_append_rows")]


def _request(text: str, ui: dict | None = None, after: list | None = None) -> dict:
    content = text
    if ui is not None:
        content += (
            "\n\n<additional context>\n" + json.dumps({"excel_ui": ui}, ensure_ascii=False) + "\n</additional context>"
        )
    return {"model": "offline", "tools": TOOLS, "input": [{"role": "user", "content": content}, *(after or [])]}


def _call(name: str, args: dict, call_id: str, output: dict) -> list[dict]:
    return [
        {"type": "function_call", "call_id": call_id, "name": name, "arguments": json.dumps(args)},
        {"type": "function_call_output", "call_id": call_id, "output": json.dumps(output, ensure_ascii=False)},
    ]


def test_read_turn_splits_question_context_and_steps() -> None:
    req = _request(
        "Thêm KH-0001 vào bảng", {"headers": ["Mã KH"]}, _call("search_data", {"query": "x"}, "c1", {"a": 1})
    )
    turn = read_turn(req)
    assert turn.user_text == "Thêm KH-0001 vào bảng" and turn.ui == {"headers": ["Mã KH"]}
    assert [(s.name, s.args) for s in turn.steps] == [("search_data", {"query": "x"})]
    assert turn.output_json("search_data") == {"a": 1} and "excel_append_rows" in turn.tools


def test_rule_brain_append_flow_asks_excel_for_headers_when_missing() -> None:
    brain, text = RuleBrain(), "Thêm khách hàng KH-0001 vào bảng"
    (step,) = brain.respond(_request(text, {}))
    assert isinstance(step, Call) and step.name == "search_data" and step.arguments["query"] == "KH-0001"

    found = {"query": "KH-0001", "records": [{"Mã KH": "KH-0001", "Tên khách hàng": "A", "Email": "a@x.vn"}]}
    searched = _call("search_data", step.arguments, "c1", found)
    (step,) = brain.respond(_request(text, {}, searched))
    assert step.name == "excel_get_context"  # chưa biết tiêu đề cột → hỏi Excel

    ctx = _call("excel_get_context", {}, "c2", {"headers": ["Mã KH", "Tên khách hàng"]})
    (step,) = brain.respond(_request(text, {}, searched + ctx))
    assert step.name == "excel_append_rows"
    assert step.arguments == {"rows": [{"Mã KH": "KH-0001", "Tên khách hàng": "A"}]}

    done = _call(
        "excel_append_rows", step.arguments, "c3", {"status": "applied", "sheet": "S", "rows_added": 1, "first_row": 9}
    )
    (step,) = brain.respond(_request(text, {}, searched + ctx + done))
    assert isinstance(step, Text) and "Đã thêm 1 dòng vào sheet S (dòng 9)" in step.text


def test_script_brain_checks_number_of_calls() -> None:
    brain = ScriptBrain([[Text("một")]])
    assert brain.respond({}) == [Text("một")]
    brain.assert_complete()
    with pytest.raises(AssertionError):
        brain.respond({})


async def test_openai_sdk_reads_mock_stream() -> None:
    """Định dạng SSE của API giả lập phải đúng như OpenAI: SDK chính thức đọc ra lời gọi hàm + văn bản."""
    brain = ScriptBrain([[Call("search_data", {"query": "Huế"}, call_id="call_1"), Text("xong")]])
    client = AsyncOpenAI(api_key="test", base_url=BASE_URL, http_client=http_client(brain))
    stream = await client.responses.create(model="gpt-5-mini", input="tìm Huế", stream=True)
    kinds, final = [], None
    async for event in stream:
        kinds.append(event.type)
        if event.type == "response.completed":
            final = event.response
    assert kinds[0] == "response.created" and kinds[-1] == "response.completed"
    assert "response.function_call_arguments.delta" in kinds and "response.output_text.delta" in kinds
    assert final.output[0].name == "search_data" and final.output[0].call_id == "call_1"
    assert final.output_text == "xong" and final.usage.total_tokens > 0


async def test_mock_rejects_tool_output_without_matching_call() -> None:
    """Giống OpenAI: function_call_output phải trỏ đúng call_id của một function_call (bắt lỗi ghép id khi resume)."""
    import openai

    client = AsyncOpenAI(api_key="test", base_url=BASE_URL, http_client=http_client(ScriptBrain([[Text("x")]])))
    bad = [{"role": "user", "content": "hi"}, {"type": "function_call_output", "call_id": "fc_1", "output": "{}"}]
    with pytest.raises(openai.BadRequestError, match="fc_1"):
        await client.responses.create(model="gpt-5-mini", input=bad)
