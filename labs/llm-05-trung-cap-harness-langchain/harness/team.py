"""Team — Agno `Team(mode=...)` ↔ agent trưởng nhóm có các agent con làm tool (`make_subagent_tool`).

| Agno | LangChain |
|---|---|
| `members=[agent, ...]`, `role` của thành viên | mỗi thành viên là một tool; `description` của tool đóng vai `role` |
| `delegate_task_to_member(member_id, task)` | gọi tool của thành viên với `task` |
| `mode="coordinate"`: trưởng nhóm tổng hợp | tool thường: kết quả quay về trưởng nhóm, nó viết câu trả lời cuối |
| `mode="route"`: trả nguyên văn câu trả lời của thành viên | tool `return_direct=True`: run dừng ngay sau tool |
| `run.member_responses` | các ToolMessage trong `messages` |

Giống Agno: thành viên CHỈ nhận `task` trưởng nhóm viết, không nhận câu hỏi gốc của người dùng.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel

from harness.data import CustomerDB
from harness.improved import make_subagent_tool
from harness.tools import make_server_tools

LEAD = "Bạn là trưởng nhóm chăm sóc khách hàng. Giao tra cứu cho ask_analyst, giao viết thư cho ask_writer."
ANALYST = "Bạn là chuyên viên tra cứu khách hàng. Chỉ trả số liệu lấy từ tool."
WRITER = "Bạn là người viết thư cho khách hàng. Không thêm số liệu ngoài phần được giao."


def build_team(lead: BaseChatModel, member: Callable[[str], BaseChatModel], db: CustomerDB, mode: str = "coordinate"):
    """`member(name)` trả model cho từng thành viên (test truyền model kịch bản riêng cho mỗi người)."""
    direct = mode == "route"
    analyst = make_subagent_tool(
        "ask_analyst",
        "Tra cứu dữ liệu khách hàng: hạn mức, công nợ, trạng thái giao hàng.",
        member("analyst"),
        make_server_tools(db)[:1],
        ANALYST,
        return_direct=direct,
    )
    writer = make_subagent_tool(
        "ask_writer",
        "Viết thư cho khách hàng từ dữ liệu được giao.",
        member("writer"),
        [],
        WRITER,
        return_direct=direct,
    )
    return create_agent(lead, tools=[analyst, writer], system_prompt=LEAD, name=f"team-{mode}")


def member_answers(out: dict[str, Any]) -> list[tuple[str, str]]:
    """(tên thành viên, câu trả lời) — tương đương `run.member_responses` của Agno."""
    return [(m.name, m.content) for m in out["messages"] if m.type == "tool"]
