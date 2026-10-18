"""Phần 4 — Session: lịch sử hội thoại, session_state và tóm tắt session, đều lưu trong database.

uv run python -m agno_lab.p04_session report-01 lan "Lập báo cáo Q2"
uv run python -m agno_lab.p04_session report-01 lan "Rút tóm tắt còn 3 ý"   # cùng session: nhớ v1
"""

from __future__ import annotations

import sys

from agno.agent import Agent, RunOutput
from agno.run import RunContext

from agno_lab.p01_agent import KpiTools
from agno_lab.settings import db, model


def record_revision(run_context: RunContext, quarter: str, note: str) -> str:
    """Ghi nhận đã viết xong một phiên bản báo cáo cho quý `quarter`, kèm ghi chú ngắn về thay đổi.

    Chỉ gọi SAU khi đã viết xong nội dung của phiên bản đó.
    """
    state = run_context.session_state  # dict của session hiện tại; Agno lưu lại sau khi run xong
    state["revision"] += 1
    state["quarter"] = quarter
    state["notes"].append(f"v{state['revision']}: {note}")
    return f"Đã ghi nhận phiên bản v{state['revision']}"


def build_agent(agentic_state: bool = False) -> Agent:
    return Agent(
        id="report-assistant",
        name="Report Assistant",
        model=model(),
        db=db(),  # không có db thì không có lịch sử, state, tóm tắt
        session_state={"revision": 0, "quarter": None, "notes": []},  # giá trị khởi tạo cho session MỚI
        add_session_state_to_context=True,  # đưa state vào system prompt
        enable_agentic_state=agentic_state,  # True: thêm tool update_session_state, model tự ghi state
        add_history_to_context=True,
        num_history_runs=3,  # 3 run gần nhất của session (mặc định cũng là 3)
        enable_session_summaries=True,  # cuối mỗi run: thêm MỘT lượt gọi model để tóm tắt session
        add_session_summary_to_context=True,
        tools=[KpiTools(), record_revision],
        instructions=[
            "Bạn soạn báo cáo KPI theo nhiều phiên bản trong cùng một phiên làm việc, bằng tiếng Việt.",
            "Phiên bản hiện tại: v{revision}, quý {quarter}.",  # {…} được thay bằng giá trị trong session_state
            "Sau khi viết xong một phiên bản, gọi record_revision.",
        ],
    )


def chat(session_id: str, user_id: str, message: str) -> RunOutput:
    return build_agent().run(message, session_id=session_id, user_id=user_id)


def show(session_id: str) -> str:
    agent = build_agent()
    summary = agent.get_session_summary(session_id=session_id)
    history = agent.get_chat_history(session_id=session_id)
    return "\n".join(
        [
            f"state: {agent.get_session_state(session_id=session_id)}",
            f"summary: {summary.summary if summary else None}",
            f"history: {len(history)} message",
        ]
    )


if __name__ == "__main__":
    session_id, user_id, message = sys.argv[1:4]
    print(chat(session_id, user_id, message).content)
    print(show(session_id))
