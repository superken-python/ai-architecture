import asyncio
import json

from agno_lab.p01_agent import build_agent, describe
from mock_llm import call, say


def tool_messages(request: dict) -> list[str]:
    return [m["content"] for m in request["messages"] if m["role"] == "tool"]


def test_tool_call_and_answer(llm):
    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), say("CLOUD_OPS (KPI_02) và FIN_TECH (KPI_03) bị cảnh báo."))
    run = build_agent().run("Phòng ban nào bị cảnh báo ở 2026-Q2?")

    assert run.content == "CLOUD_OPS (KPI_02) và FIN_TECH (KPI_03) bị cảnh báo."
    (tool,) = run.tools
    assert tool.tool_name == "get_quarter_kpis" and tool.tool_args == {"quarter": "2026-Q2"}
    kpis = {row["dept_code"]: row["alert"] for row in json.loads(tool.result)}
    assert kpis == {"AI_LAB": "ĐẠT", "CLOUD_OPS": "CẢNH BÁO VÀNG", "FIN_TECH": "YÊU CẦU GIẢI TRÌNH"}
    # lượt gọi model thứ 2 nhận kết quả tool — đó là vòng lặp agent
    assert "CẢNH BÁO VÀNG" in tool_messages(llm.requests[1])[0]
    assert run.metrics.total_tokens > 0
    assert "tool get_quarter_kpis" in describe(run)


def test_tools_are_sent_as_json_schema(llm):
    llm.script(say("ok"))
    build_agent().run("chào")
    tools = {t["function"]["name"]: t["function"] for t in llm.requests[0]["tools"]}
    assert set(tools) == {"inspect_rules", "get_quarter_kpis"}
    assert tools["get_quarter_kpis"]["parameters"]["properties"]["quarter"]["type"] == "string"
    assert "Dùng khi người dùng hỏi số liệu" in tools["get_quarter_kpis"]["description"]  # docstring → mô tả


def test_bad_quarter_returns_guidance_and_model_retries(llm):
    llm.script(
        call("get_quarter_kpis", quarter="Q2-2026"),
        call("get_quarter_kpis", quarter="2026-Q2"),
        say("Đã sửa quý và lấy được số liệu."),
    )
    run = build_agent().run("KPI quý 2 năm 2026")
    first, second = run.tools
    assert first.result.startswith("Lỗi: quarter phải có dạng YYYY-Q1..Q4")
    assert json.loads(second.result)[0]["dept_code"] == "AI_LAB"


def test_async_run(llm):
    llm.script(say("xin chào"))
    run = asyncio.run(build_agent().arun("chào"))
    assert run.content == "xin chào"
