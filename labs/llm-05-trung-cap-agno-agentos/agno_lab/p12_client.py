"""Phần 12 (tiếp) — Gọi AgentOS từ một chương trình khác bằng AgentOSClient (client có kiểu của Agno).

Phần lớn phương thức của AgentOSClient là async (dù tên không có tiền tố `a`) → dùng await.

    uv run python -m agno_lab.p12_client
"""

from __future__ import annotations

import asyncio
import json
import os

from agno.client.os import AgentOSClient
from agno.db.base import SessionType

from agno_lab.p02_structured import ReportRequest


def headers() -> dict[str, str]:
    key = os.getenv("OS_SECURITY_KEY")
    return {"Authorization": f"Bearer {key}"} if key else {}


async def demo(base_url: str = "http://localhost:7777") -> dict:
    client = AgentOSClient(base_url=base_url, timeout=120)
    result: dict = {"agents": [a.id for a in await client.list_agents(headers=headers())]}

    run = await client.run_agent(
        "kpi-analyst", "Phòng ban nào bị cảnh báo ở 2026-Q2?", session_id="api-01", user_id="lan", headers=headers()
    )
    result["answer"] = run.content

    sessions = await client.get_sessions(session_type=SessionType.AGENT, user_id="lan", headers=headers())
    result["sessions"] = [s.session_id for s in sessions.data]

    # Workflow có input_schema: gửi JSON của ReportRequest làm message
    request = ReportRequest(quarter="2026-Q2", instruction="Lập báo cáo, nêu rủi ro")
    wf = await client.run_workflow(
        "report-workflow", json.dumps(request.model_dump()), session_id="api-wf", headers=headers()
    )
    result["workflow_paused_at"] = wf.paused_step_name
    if wf.is_paused:
        for requirement in wf.step_requirements:
            requirement.confirm()
        wf = await client.continue_workflow_run(
            "report-workflow", wf.run_id, wf.step_requirements, session_id="api-wf", headers=headers()
        )
    result["workflow_status"] = getattr(wf.status, "value", wf.status)  # qua client, status có thể là chuỗi

    traces = await client.get_traces(session_id="api-01", headers=headers())
    result["traces"] = len(traces.data)
    return result


if __name__ == "__main__":
    for key, value in asyncio.run(demo()).items():
        print(f"{key}: {value}")
