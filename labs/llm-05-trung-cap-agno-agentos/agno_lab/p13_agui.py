"""Phần 13 — AG-UI: giao thức agent ↔ giao diện. AgentOS phát sự kiện chuẩn qua SSE ở POST /agui.

Agent ở đây có session_state (revision, quarter) — AG-UI đồng bộ state này lên giao diện bằng STATE_SNAPSHOT/
STATE_DELTA. Client (frontend) có thể khai báo tool của riêng nó (frontend tool): server phát TOOL_CALL_* rồi dừng
run; client tự chạy tool trên giao diện và gửi kết quả trong request kế tiếp, run chạy tiếp (như CMB-10).

    uv run python -m agno_lab.p12_os                                       # terminal 1: AgentOS có /agui
    uv run python -m agno_lab.p13_agui "Tô màu phòng bị cảnh báo 2026-Q2"    # terminal 2: client giả lập giao diện
"""

from __future__ import annotations

import json
import sys
import uuid
from typing import Any

import httpx
from agno.agent import Agent

from agno_lab.p01_agent import KpiTools
from agno_lab.p04_session import record_revision
from agno_lab.p12_client import headers as auth_headers
from agno_lab.settings import db, model


def agui_agent() -> Agent:
    return Agent(
        id="report-ui",
        name="Report UI Agent",
        model=model(),
        db=db(),  # AG-UI threadId = session_id; tool client tạm dừng cần db để chạy tiếp
        session_state={"revision": 0, "quarter": None, "notes": []},
        tools=[KpiTools(), record_revision],
        add_history_to_context=True,
        instructions=[
            "Bạn soạn báo cáo KPI trong giao diện web, trả lời tiếng Việt.",
            "Viết xong một bản thì gọi record_revision.",
        ],
    )


def run_input(thread_id: str, text: str, tools: list[dict] | None = None, state: dict | None = None) -> dict:
    """RunAgentInput của AG-UI (JSON camelCase). threadId = session_id; `tools` = frontend tool của giao diện."""
    return {
        "threadId": thread_id,
        "runId": uuid.uuid4().hex,
        "state": state or {},  # state giao diện đang giữ; key trùng sẽ GHI ĐÈ session_state trên server
        "messages": [{"id": uuid.uuid4().hex, "role": "user", "content": text}],
        "tools": tools or [],
        "context": [],
        "forwardedProps": {},
    }


# Frontend tool: giao diện khai báo bằng JSON Schema, server KHÔNG có code của tool này.
HIGHLIGHT = {
    "name": "highlight_departments",
    "description": "Tô màu các dòng phòng ban trên bảng KPI của giao diện",
    "parameters": {
        "type": "object",
        "properties": {"departments": {"type": "array", "items": {"type": "string"}}},
        "required": ["departments"],
    },
}


def parse_sse(lines: list[str]) -> list[dict]:
    return [json.loads(line[len("data: ") :]) for line in lines if line.startswith("data: ")]


def stream_events(base_url: str, payload: dict, headers: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """Client tối giản: gửi RunAgentInput, đọc SSE, trả danh sách sự kiện."""
    with httpx.stream("POST", f"{base_url}/agui", json=payload, headers=headers, timeout=120) as response:
        response.raise_for_status()
        return parse_sse(list(response.iter_lines()))


def pending_frontend_calls(events: list[dict], frontend_tools: set[str]) -> list[dict]:
    """Tool call của frontend trong stream: có TOOL_CALL_START/ARGS/END nhưng không có TOOL_CALL_RESULT."""
    calls: dict[str, dict] = {}
    for event in events:
        if event["type"] == "TOOL_CALL_START" and event["toolCallName"] in frontend_tools:
            calls[event["toolCallId"]] = {"id": event["toolCallId"], "name": event["toolCallName"], "arguments": ""}
        elif event["type"] == "TOOL_CALL_ARGS" and event["toolCallId"] in calls:
            calls[event["toolCallId"]]["arguments"] += event["delta"]  # tham số đến theo từng mảnh
    done = {e["toolCallId"] for e in events if e["type"] == "TOOL_CALL_RESULT"}
    return [c for c in calls.values() if c["id"] not in done]


def resume_input(previous: dict, pending: list[dict], results: dict[str, str]) -> dict:
    """RunAgentInput chạy tiếp: lịch sử + tin assistant có toolCalls + một tin `tool` cho mỗi kết quả (theo id)."""
    assistant = {
        "id": uuid.uuid4().hex,
        "role": "assistant",
        "toolCalls": [
            {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}
            for c in pending
        ],
    }
    answers = [
        {"id": uuid.uuid4().hex, "role": "tool", "toolCallId": c["id"], "content": results[c["id"]]} for c in pending
    ]
    return {**previous, "runId": uuid.uuid4().hex, "messages": [*previous["messages"], assistant, *answers]}


def print_events(events: list[dict]) -> None:
    for event in events:
        extra = event.get("delta") or event.get("toolCallName") or event.get("snapshot") or ""
        print(f"{event['type']:<24} {str(extra)[:80]}")


if __name__ == "__main__":
    base = "http://localhost:7777"
    payload = run_input(
        "ui-demo", sys.argv[1] if len(sys.argv) > 1 else "Tô màu phòng bị cảnh báo 2026-Q2", tools=[HIGHLIGHT]
    )
    events = stream_events(base, payload, auth_headers())  # Bearer nếu có OS_SECURITY_KEY
    print_events(events)
    pending = pending_frontend_calls(events, {HIGHLIGHT["name"]})
    if pending:  # "giao diện" chạy tool rồi gửi kết quả về
        results = {}
        for c in pending:
            departments = json.loads(c["arguments"])["departments"]
            print(f"[UI] tô màu {departments}")
            results[c["id"]] = f"Đã tô {len(departments)} dòng"
        print_events(stream_events(base, resume_input(payload, pending, results), auth_headers()))
