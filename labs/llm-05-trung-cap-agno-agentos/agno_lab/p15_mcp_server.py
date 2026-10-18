"""Phần 15 — AgentOS làm MCP SERVER: Claude Code, Claude Desktop, Cursor... gọi agent của bạn như một tool.

Phần 9 là chiều ngược lại (agent của ta là MCP client đọc server dữ liệu). Ở đây AgentOS mở endpoint MCP /mcp:
- mcp=True       → 8 tool mặc định: get_agentos_config, run_agent, run_team, run_workflow, continue_run, cancel_run,
                    get_sessions, get_session_runs. Client tự khám phá id rồi gọi run_agent(agent_id, message).
- MCPConfig(...) → chỉ công bố đúng các tool bạn chọn: agent.as_tool(...) là một tool chạy agent, với tên và mô tả
                    viết cho model ở phía client; hàm thường thì chạy thẳng, không tốn lượt gọi model.
OS_SECURITY_KEY khoá cả /mcp (cần header Authorization: Bearer ...); /mcp/server-card luôn công khai.

    uv run python -m agno_lab.p15_mcp_server serve                                  # http://localhost:7778/mcp
    uv run python -m agno_lab.p15_mcp_server ask "Phòng nào bị cảnh báo 2026-Q2?"    # client MCP gọi thử
"""

from __future__ import annotations

import asyncio
import sys

import httpx2  # mcp 2.x dùng httpx2 (không phải httpx) cho transport HTTP
from agno.os import AgentOS
from agno.os.config import MCPConfig
from fastapi import FastAPI
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from agno_lab import p01_agent
from agno_lab.p12_client import headers
from agno_lab.settings import db


def build_mcp_os(default_tools: bool = False) -> AgentOS:
    analyst = p01_agent.build_agent()
    curated = MCPConfig(
        instructions="Công cụ báo cáo KPI nội bộ. Số liệu và cảnh báo: ask_kpi_analyst. Luật KPI: inspect_rules.",
        tools=[
            # tool chạy agent: client chỉ thấy tên + mô tả này, không thấy instructions hay tool bên trong agent
            analyst.as_tool(
                name="ask_kpi_analyst",
                description="Hỏi chuyên viên KPI về số liệu và cảnh báo của một quý dạng YYYY-Qn. Trả lời tiếng Việt.",
            ),
            p01_agent.inspect_rules,  # hàm thường: chạy thẳng trên server
        ],
    )
    return AgentOS(
        id="report-mcp",
        name="Report MCP",
        agents=[analyst],  # agent được as_tool phải nằm trong AgentOS
        db=db(),
        mcp=True if default_tools else curated,
        base_app=FastAPI(title="Report MCP", telemetry={"tracing": False}),
    )


def create_mcp_app():
    return build_mcp_os().get_app()


async def ask(url: str, question: str) -> dict:
    """Một MCP client bất kỳ (ở đây là SDK mcp 2.x) gọi agent qua /mcp."""
    timeout = httpx2.Timeout(30, read=300)  # agent có thể chạy lâu: đọc chờ tới 300 giây
    async with (
        httpx2.AsyncClient(headers=headers(), timeout=timeout) as http,  # có OS_SECURITY_KEY thì gửi Bearer
        Client(streamable_http_client(url, http_client=http)) as client,
    ):
        tools = [t.name for t in (await client.list_tools()).tools]
        result = await client.call_tool("ask_kpi_analyst", {"message": question})
        return {
            "tools": tools,
            "is_error": result.is_error,
            "text": "\n".join(part.text for part in result.content if part.type == "text"),
            "run": result.structured_content,  # run_id, session_id, status, agent_id — đủ để hỏi tiếp cùng session
        }


if __name__ == "__main__":
    if sys.argv[1] == "serve":
        import uvicorn

        uvicorn.run("agno_lab.p15_mcp_server:create_mcp_app", factory=True, host="127.0.0.1", port=7778)
    else:
        print(asyncio.run(ask("http://localhost:7778/mcp", sys.argv[2])))
