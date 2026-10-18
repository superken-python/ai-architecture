"""Phần 10 — Team: nhiều agent chuyên trách, một trưởng nhóm điều phối theo 4 chế độ.

uv run python -m agno_lab.p10_team coordinate "Lập báo cáo KPI 2026-Q2"
uv run python -m agno_lab.p10_team route      "Ngưỡng của KPI_02 là bao nhiêu?"
uv run python -m agno_lab.p10_team broadcast  "Đánh giá rủi ro quý 2026-Q2"
"""

from __future__ import annotations

import sys

from agno.agent import Agent
from agno.team import Team

from agno_lab.p01_agent import KpiTools, inspect_rules
from agno_lab.settings import db, model

LEAD = "Bạn là trưởng nhóm báo cáo KPI."  # chuỗi đầu instructions — test dùng để nhận ra lượt gọi của từng agent
ANALYST = "Bạn là chuyên viên phân tích KPI."
WRITER = "Bạn là người viết báo cáo điều hành."
RISK = "Bạn là chuyên viên rủi ro."


def analyst() -> Agent:
    return Agent(
        id="kpi-analyst",
        name="KPI Analyst",
        role="Lấy số liệu KPI và giải thích cảnh báo theo rule",  # trưởng nhóm đọc role để chọn người
        model=model(),
        tools=[KpiTools(), inspect_rules],
        instructions=[ANALYST, "Chỉ trả số liệu và cảnh báo lấy từ tool, kèm rule_id."],
    )


def writer() -> Agent:
    return Agent(
        id="narrative-writer",
        name="Narrative Writer",
        role="Viết tóm tắt điều hành và hành động từ số liệu được giao",
        model=model(),
        instructions=[WRITER, "Không tự thêm số liệu ngoài phần được giao."],
    )


def risk_reviewer() -> Agent:
    return Agent(
        id="risk-reviewer",
        name="Risk Reviewer",
        role="Đánh giá rủi ro tài chính từ KPI",
        model=model(),
        tools=[KpiTools()],
        instructions=[RISK, "Nêu tối đa 2 rủi ro, mỗi rủi ro một câu."],
    )


def build_team(mode: str = "coordinate") -> Team:
    members = [analyst(), writer()] if mode != "broadcast" else [analyst(), risk_reviewer()]
    return Team(
        id=f"report-team-{mode}",
        name="Report Team",
        mode=mode,  # coordinate | route | broadcast | tasks
        model=model(),  # model của trưởng nhóm
        members=members,
        db=db(),
        add_history_to_context=True,
        store_member_responses=True,  # lưu câu trả lời của thành viên vào run → xem lại được
        instructions=[
            LEAD,
            "Giao việc lấy số liệu cho kpi-analyst; giao việc viết cho narrative-writer kèm số liệu đã có.",
            "Câu trả lời cuối bằng tiếng Việt, không thêm số liệu ngoài kết quả của thành viên.",
        ],
    )


if __name__ == "__main__":
    mode, question = sys.argv[1], sys.argv[2]
    run = build_team(mode).run(question, session_id=f"team-{mode}")
    for member in run.member_responses or []:
        print(f"--- {getattr(member, 'agent_id', '?')}: {member.content}")
    print("=== trả lời:", run.content)
