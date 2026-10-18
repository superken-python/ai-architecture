import asyncio

import httpx
from agno.tools.mcp import MCPTools
from mcp import Client

from agno_lab.p09_mcp import ask as agent_ask
from agno_lab.p15_mcp_server import ask, build_mcp_os
from mock_llm import call, say, serve_in_thread

ANALYST = "Luôn lấy số liệu bằng get_quarter_kpis"
DEFAULT_TOOLS = [
    "get_agentos_config",
    "run_agent",
    "run_team",
    "run_workflow",
    "continue_run",
    "cancel_run",
    "get_sessions",
    "get_session_runs",
]


async def tool_names(url: str) -> list[str]:
    async with Client(url) as client:
        return [t.name for t in (await client.list_tools()).tools]


def test_mcp_true_serves_the_eight_default_tools():
    base = serve_in_thread(build_mcp_os(default_tools=True).get_app())
    assert asyncio.run(tool_names(f"{base}/mcp")) == DEFAULT_TOOLS


def test_curated_surface_exposes_only_chosen_tools(llm):
    base = serve_in_thread(build_mcp_os().get_app())

    async def check():
        async with Client(f"{base}/mcp") as client:
            assert "ask_kpi_analyst" in client.instructions
            tools = {t.name: t for t in (await client.list_tools()).tools}
            assert list(tools) == ["inspect_rules", "ask_kpi_analyst"]
            assert list(tools["ask_kpi_analyst"].input_schema["properties"]) == ["message", "user_id", "session_id"]
            rules = await client.call_tool("inspect_rules", {})
            return rules

    rules = asyncio.run(check())
    assert '"rule_id": "KPI_02"' in rules.content[0].text
    assert llm.requests == []  # hàm thường chạy thẳng, không gọi model


def test_an_mcp_client_runs_the_agent(llm):
    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), say("CLOUD_OPS và FIN_TECH bị cảnh báo."), match=ANALYST)
    base = serve_in_thread(build_mcp_os().get_app())
    result = asyncio.run(ask(f"{base}/mcp", "Phòng nào bị cảnh báo 2026-Q2?"))
    assert result["text"] == "CLOUD_OPS và FIN_TECH bị cảnh báo." and not result["is_error"]
    assert result["run"]["status"] == "COMPLETED" and result["run"]["agent_id"] == "kpi-analyst"


def test_security_key_also_guards_mcp(llm, monkeypatch):
    monkeypatch.setenv("OS_SECURITY_KEY", "khoa")  # như khi chạy: OS_SECURITY_KEY=khoa uv run ...
    base = serve_in_thread(build_mcp_os().get_app())
    accept = {"Accept": "application/json, text/event-stream"}
    assert (
        httpx.post(f"{base}/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers=accept).status_code
        == 401
    )
    assert httpx.get(f"{base}/mcp/server-card").status_code == 200  # card công khai, chỉ liệt kê tên tool

    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), say("Có 2 phòng bị cảnh báo."), match=ANALYST)
    result = asyncio.run(ask(f"{base}/mcp", "Phòng nào bị cảnh báo 2026-Q2?"))  # ask() gửi Bearer từ OS_SECURITY_KEY
    assert result["text"] == "Có 2 phòng bị cảnh báo."


def test_an_agno_agent_can_use_another_agentos_through_mcp(llm):
    """Vòng khép kín: agent MCP client của Phần 9 dùng AgentOS của Phần 15 làm MCP server."""
    question = "Phòng nào bị cảnh báo 2026-Q2?"
    llm.script(
        call("ask_kpi_analyst", message=question), say("Theo chuyên viên KPI: CLOUD_OPS, FIN_TECH.")
    )  # agent gọi
    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), say("CLOUD_OPS và FIN_TECH bị cảnh báo."), match=ANALYST)
    base = serve_in_thread(build_mcp_os().get_app())
    tools = MCPTools(
        url=f"{base}/mcp", transport="streamable-http", include_tools=["ask_kpi_analyst"], timeout_seconds=60
    )
    run = asyncio.run(agent_ask(question, tools))
    assert run.content == "Theo chuyên viên KPI: CLOUD_OPS, FIN_TECH."
    assert "CLOUD_OPS và FIN_TECH bị cảnh báo." in run.tools[0].result  # câu trả lời của agent bên kia
