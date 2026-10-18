"""Phần 12 — AgentOS: một ứng dụng FastAPI phục vụ mọi agent, team, workflow của các phần trước.

Có sẵn: REST chạy run (thường/stream), chạy tiếp run tạm dừng, session, memory, knowledge, eval, trace,
metrics, lịch (scheduler) — cộng các interface AG-UI (Phần 13), A2A (Phần 14), MCP server (Phần 15).

    uv run python -m agno_lab.p12_os                 # http://localhost:7777  — tài liệu API: /docs
    OS_SECURITY_KEY=bi-mat uv run python -m agno_lab.p12_os   # bắt buộc header Authorization: Bearer bi-mat
"""

from __future__ import annotations

from agno.os import AgentOS
from agno.os.interfaces.agui import AGUI
from agno.os.settings import AgnoAPISettings
from fastapi import FastAPI

from agno_lab import p01_agent, p02_structured, p04_session, p05_memory, p07_tools_hitl, p10_team, p11_workflow
from agno_lab.p13_agui import agui_agent
from agno_lab.settings import db


def build_os(*, tracing: bool = True, mcp: bool = False, settings: AgnoAPISettings | None = None) -> AgentOS:
    analyst = p01_agent.build_agent()
    return AgentOS(
        id="enterprise-report-os",
        name="Enterprise Report OS",
        description="Agent, team và workflow lập báo cáo KPI của Lab 01",
        agents=[
            analyst,
            p02_structured.build_writer(),
            p04_session.build_agent(),
            p05_memory.build_agent(),
            p07_tools_hitl.build_agent(),
        ],
        teams=[p10_team.build_team("coordinate")],
        workflows=[p11_workflow.build_workflow()],
        db=db(),  # db mặc định cho thành phần nào chưa có db; cũng là nơi lưu trace, eval
        interfaces=[AGUI(agent=agui_agent())],  # Phần 13: POST /agui
        a2a_interface=True,  # Phần 14: mọi agent/team/workflow nói A2A ở /a2a/...
        mcp=mcp,  # True → thêm MCP server ở /mcp với 8 tool mặc định; tự chọn tool: MCPConfig (Phần 15)
        tracing=tracing,  # OpenTelemetry: mỗi run thành trace + span, lưu vào db, xem ở /traces
        # FastAPI >= 0.140 tự sinh span HTTP khi có OpenTelemetry → span HTTP thành gốc trace, trace mất agent_id/
        # session_id (lọc /traces theo session ra rỗng). Tắt tracing native của FastAPI để span agent là gốc.
        base_app=FastAPI(title="Enterprise Report OS", telemetry={"tracing": False}),
        settings=settings,  # None → đọc biến môi trường (OS_SECURITY_KEY, ...)
    )


def create_app():
    """Factory cho uvicorn: chỉ dựng app khi server khởi động (đã đọc .env), không dựng lúc import module."""
    return build_os().get_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("agno_lab.p12_os:create_app", factory=True, host="127.0.0.1", port=7777)
