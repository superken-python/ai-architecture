"""Phần 7 — Tool nâng cao và người trong vòng lặp (HITL): xác nhận, hỏi thêm, tool chạy ở client, hook.

uv run python -m agno_lab.p07_tools_hitl "Lập báo cáo Q2 rồi lưu lại, giao người phụ trách"
"""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Callable
from typing import Any

from agno.agent import Agent, RunOutput
from agno.tools import tool

from agno_lab.p01_agent import KpiTools
from agno_lab.settings import db, model
from reporting import save_local_report

AUDIT: list[dict] = []  # nhật ký mỗi lần gọi tool, do hook ghi


def audit_hook(function_name: str, function_call: Callable, arguments: dict[str, Any]) -> Any:
    """Tool hook = middleware quanh MỌI lần gọi tool: đo thời gian, ghi log, chặn, sửa đối số..."""
    started = time.perf_counter()
    result = function_call(**arguments)  # gọi tool thật (hoặc hook kế tiếp trong chuỗi)
    AUDIT.append({"tool": function_name, "args": arguments, "ms": round((time.perf_counter() - started) * 1000, 1)})
    return result


@tool(requires_confirmation=True)  # run DỪNG trước khi chạy tool, chờ người duyệt
def save_report(report_id: str, revision: int, markdown: str) -> str:
    """Lưu báo cáo Markdown thành file storage/<report_id>/v<revision>.md."""
    save_local_report(report_id, revision, markdown)
    return f"Đã lưu {report_id}/v{revision}.md"


@tool(requires_user_input=True, user_input_fields=["owner"])  # run DỪNG để người dùng điền `owner`
def assign_owner(action: str, owner: str) -> str:
    """Giao một hành động trong báo cáo cho người phụ trách (owner do người dùng chọn)."""
    return f"Đã giao '{action}' cho {owner}"


@tool(external_execution=True)  # Agno KHÔNG chạy hàm này: client (add-in, UI) chạy rồi gửi kết quả về
def export_to_excel(sheet: str, rows: list[dict]) -> str:
    """Ghi các dòng KPI vào một sheet Excel đang mở ở phía người dùng."""
    raise NotImplementedError("chạy ở client")


@tool(stop_after_tool_call=True, show_result=True)  # trả kết quả thẳng cho người dùng, không gọi model thêm
def publish_notice(text: str) -> str:
    """Đăng thông báo cuối cùng cho người dùng; dùng khi công việc đã xong."""
    return f"THÔNG BÁO: {text}"


def build_agent() -> Agent:
    return Agent(
        id="report-operator",
        name="Report Operator",
        model=model(),
        db=db(),  # run tạm dừng được lưu vào DB → chạy tiếp được cả sau khi khởi động lại process
        tools=[KpiTools(cache_results=True), save_report, assign_owner, export_to_excel, publish_notice],
        tool_hooks=[audit_hook],
        instructions=[
            "Bạn lập, lưu và phân công báo cáo KPI bằng tiếng Việt.",
            "Lưu báo cáo bằng save_report; giao việc bằng assign_owner; xuất Excel bằng export_to_excel.",
        ],
    )


Decide = Callable[[Any], None]


def resolve(agent: Agent, run: RunOutput, decide: Decide) -> RunOutput:
    """Vòng xử lý run tạm dừng: `decide` quyết từng yêu cầu, rồi continue_run cho tới khi run không còn dừng."""
    while run.is_paused:
        for requirement in run.active_requirements:
            decide(requirement)
        run = agent.continue_run(run_response=run, requirements=run.requirements)
    return run


def console_decide(requirement: Any) -> None:
    """Ví dụ hỏi người dùng ở terminal."""
    tool_execution = requirement.tool_execution
    if requirement.needs_confirmation:
        answer = input(f"Cho phép {tool_execution.tool_name}({tool_execution.tool_args})? [y/N] ")
        requirement.confirm() if answer.lower() == "y" else requirement.reject("Người dùng không đồng ý")
    elif requirement.needs_user_input:
        requirement.provide_user_input({"owner": input(f"Người phụ trách cho {tool_execution.tool_args}: ")})
    elif requirement.needs_external_execution:
        requirement.set_external_execution_result(json.dumps({"written": len(tool_execution.tool_args["rows"])}))


if __name__ == "__main__":
    agent = build_agent()
    run = agent.run(sys.argv[1] if len(sys.argv) > 1 else "Lập báo cáo Q2 rồi lưu lại", session_id="ops-01")
    print(resolve(agent, run, console_decide).content)
    print("audit:", AUDIT)
