import asyncio
import json

import pytest

from agno_lab.p09_mcp import ask, http_tools, stdio_tools, wrapper_agent
from mock_llm import call, say
from servers import free_port, process_server


def tool_payload(run) -> list[dict]:
    """Wrapper trả một mảng JSON; MCPTools trả các JSON object nối nhau bằng xuống dòng (mỗi TextContent một object)."""
    (tool,) = run.tools
    text, rows, decoder, i = tool.result.strip(), [], json.JSONDecoder(), 0
    while i < len(text):
        value, i = decoder.raw_decode(text, i)
        rows.extend(value if isinstance(value, list) else [value])
        while i < len(text) and text[i].isspace():
            i += 1
    return rows


def test_wrapper_tool_calls_the_mcp_server(llm):
    llm.script(call("fetch_quarter_metrics", quarter="2026-Q2"), say("AI_LAB đạt 620.000 USD."))
    run = asyncio.run(wrapper_agent().arun("Doanh thu 2026-Q2?"))
    rows = tool_payload(run)
    assert {r["dept_code"]: r["revenue_usd"] for r in rows}["AI_LAB"] == 620000
    assert run.content == "AI_LAB đạt 620.000 USD."


def test_wrapper_reports_server_errors(llm):
    llm.script(call("fetch_quarter_metrics", quarter="Q2"), say("Quý sai định dạng."))
    run = asyncio.run(wrapper_agent().arun("Doanh thu Q2?"))
    assert run.tools[0].result.startswith("Lỗi MCP:") and "YYYY-Q1..Q4" in run.tools[0].result


def test_mcptools_stdio_discovers_tools_from_the_server(llm):
    llm.script(call("get_metrics", quarter="2026-Q2"), say("Đã đọc qua MCP."))
    run = asyncio.run(ask("Doanh thu 2026-Q2?", stdio_tools()))
    tools = {t["function"]["name"]: t["function"] for t in llm.requests[0]["tools"]}
    assert list(tools) == ["get_metrics"]  # schema lấy từ server, không viết trong code agent
    assert "không nhận SQL tự do" in tools["get_metrics"]["description"]
    assert {r["dept_code"] for r in tool_payload(run)} == {"AI_LAB", "CLOUD_OPS", "FIN_TECH"}


@pytest.fixture
def http_server():
    port = free_port()
    with process_server(["mcp_db_server.py", "--http", str(port)], port) as url:
        yield f"{url}/mcp"


def test_mcptools_streamable_http(llm, http_server):
    llm.script(call("get_metrics", quarter="2026-Q1"), say("Đã đọc qua MCP HTTP."))
    run = asyncio.run(ask("Doanh thu 2026-Q1?", http_tools(http_server)))
    assert {r["dept_code"]: r["cost_usd"] for r in tool_payload(run)}["CLOUD_OPS"] == 720000
