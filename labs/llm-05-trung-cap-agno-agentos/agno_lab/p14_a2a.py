"""Phần 14 — A2A: gọi một agent chạy ở DỊCH VỤ KHÁC qua giao thức Agent-to-Agent.

Theo Lab 00 §9: research là dịch vụ riêng ở cổng 8001, trả kết quả có provenance và cờ fixture/live.
Dịch vụ là một AgentOS bật A2A; phía gọi dùng A2AClient, hoặc RemoteAgent để đưa agent ở xa vào Team.

    uv run python -m agno_lab.p14_a2a serve                          # terminal 1: research service :8001
    uv run python -m agno_lab.p14_a2a ask "Benchmark chi phí cloud?"    # terminal 2: gọi bằng A2AClient
    uv run python -m agno_lab.p14_a2a team "So sánh FinTech với thị trường"  # Team có thành viên ở xa
"""

from __future__ import annotations

import asyncio
import json
import sys

from agno.agent import Agent
from agno.agent.remote import RemoteAgent
from agno.client.a2a import A2AClient
from agno.os import AgentOS
from agno.team import Team
from fastapi import FastAPI

from agno_lab.p10_team import analyst
from agno_lab.settings import db, model

RESEARCH = "Bạn là agent nghiên cứu thị trường."
REMOTE_LEAD = "Bạn là trưởng nhóm báo cáo có thành viên ở xa."
AGENT_ID = "market-research"


def lookup_market(topic: str) -> str:
    """Tra cứu thông tin thị trường theo chủ đề. Dữ liệu fixture: không gọi web, không có benchmark."""
    return json.dumps(
        {
            "query": topic,
            "mode": "fixture",
            "summary": "Chưa bật live search; không có benchmark thị trường.",
            "sources": [],
        },
        ensure_ascii=False,
    )


def research_agent() -> Agent:
    return Agent(
        id=AGENT_ID,
        name="Market Research",
        description="Tra cứu thông tin thị trường, luôn ghi rõ nguồn và chế độ fixture/live",  # vào Agent Card
        model=model(),
        tools=[lookup_market],
        add_history_to_context=True,  # contextId của A2A = session_id → tin nhắn sau thấy tin nhắn trước
        instructions=[RESEARCH, "Chỉ trả lời dựa trên lookup_market. Không tạo số liệu hay nguồn web."],
    )


def research_service() -> AgentOS:
    return AgentOS(
        id="research-service",
        agents=[research_agent()],
        a2a_interface=True,  # /a2a/agents/market-research/... : agent card, message:send, message:stream, tasks
        db=db(),
        base_app=FastAPI(title="Research Service", telemetry={"tracing": False}),
    )


def create_research_app():
    return research_service().get_app()


def research_url(base: str = "http://localhost:8001") -> str:
    """URL A2A ở cấp agent; client tự thêm /v1/message:send, /.well-known/agent-card.json."""
    return f"{base}/a2a/agents/{AGENT_ID}"


async def ask_research(question: str, base: str = "http://localhost:8001", context_id: str | None = None) -> dict:
    client = A2AClient(research_url(base), timeout=120)
    card = await client.aget_agent_card()  # discovery: tên, mô tả, khả năng (streaming...)
    result = await client.send_message(question, context_id=context_id)  # context_id = session ở phía server
    return {"agent": card.name, "status": result.status, "context_id": result.context_id, "answer": result.content}


def remote_research(base: str = "http://localhost:8001") -> RemoteAgent:
    """Agent ở xa, dùng như agent cục bộ — kể cả làm thành viên Team."""
    return RemoteAgent(base_url=research_url(base), agent_id=AGENT_ID, protocol="a2a", timeout=120)


def team_with_remote_member(base: str = "http://localhost:8001") -> Team:
    """Team trộn agent cục bộ và agent ở xa. Phải chạy bằng `await team.arun(...)`: RemoteAgent chỉ có API async,
    `team.run()` đồng bộ sẽ báo lỗi "'RemoteAgent' object has no attribute 'run'"."""
    return Team(
        id="report-team-a2a",
        name="Report Team (A2A)",
        model=model(),
        members=[analyst(), remote_research(base)],
        instructions=[REMOTE_LEAD, "Số liệu hỏi kpi-analyst; thị trường hỏi market-research."],
    )


async def ask_team(question: str, base: str = "http://localhost:8001") -> str:
    run = await team_with_remote_member(base).arun(question, session_id="a2a-team")
    for member in run.member_responses or []:
        print(f"--- {getattr(member, 'agent_id', '?')}: {member.content}")
    return run.content


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "serve":
        import uvicorn

        uvicorn.run("agno_lab.p14_a2a:create_research_app", factory=True, host="127.0.0.1", port=8001)
    elif command == "team":
        print("=== trả lời:", asyncio.run(ask_team(sys.argv[2])))
    else:
        print(asyncio.run(ask_research(sys.argv[2])))
