"""Phần 5 — Memory dài hạn theo người dùng: tự động sau mỗi run, hoặc để agent tự quyết khi nào ghi.

uv run python -m agno_lab.p05_memory lan "Tôi là Lan, phụ trách khối Cloud, thích báo cáo ngắn"
uv run python -m agno_lab.p05_memory lan "Tóm tắt KPI cho tôi"     # session mới vẫn nhớ Lan
"""

from __future__ import annotations

import sys
import uuid

from agno.agent import Agent, RunOutput
from agno.memory import MemoryManager

from agno_lab.p01_agent import KpiTools
from agno_lab.settings import db, model

CAPTURE = (
    "Chỉ nhớ thông tin ổn định về NGƯỜI DÙNG: tên, vai trò, phòng ban phụ trách, cách trình bày báo cáo ưa thích. "
    "KHÔNG nhớ số liệu KPI, kết quả tra cứu, hay yêu cầu tạm thời của một lần."
)


def build_agent(agentic: bool = False) -> Agent:
    return Agent(
        id="memory-assistant",
        name="Memory Assistant",
        model=model(),
        db=db(),
        # Trình trích xuất memory dùng model RIÊNG truyền vào (có thể rẻ hơn model chính).
        memory_manager=MemoryManager(model=model(), db=db(), memory_capture_instructions=CAPTURE),
        update_memory_on_run=not agentic,  # tự động: mỗi run thêm MỘT lượt gọi model trích memory từ tin nhắn user
        enable_agentic_memory=agentic,  # agent có tool update_user_memory, tự quyết khi nào ghi
        tools=[KpiTools()],
        instructions=["Trả lời bằng tiếng Việt. Cá nhân hoá theo memory về người dùng nếu có."],
    )


def ask(user_id: str | None, message: str, session_id: str | None = None, agentic: bool = False) -> RunOutput:
    if not user_id:
        # Agno gom mọi run thiếu user_id vào user "default" → memory của nhiều người trộn vào nhau.
        raise ValueError("Cần user_id để đọc/ghi memory")
    return build_agent(agentic).run(message, user_id=user_id, session_id=session_id or uuid.uuid4().hex)


def memories(user_id: str) -> list[str]:
    return [m.memory for m in build_agent().get_user_memories(user_id=user_id)]


if __name__ == "__main__":
    user, message = sys.argv[1], sys.argv[2]
    print(ask(user, message).content)
    print("memory:", memories(user))
