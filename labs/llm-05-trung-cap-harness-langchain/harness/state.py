"""State của session — Agno `session_state` ↔ trường riêng trong state của LangGraph.

- `session_state={"revision": 0, ...}` ↔ `class DraftState(AgentState): revision: NotRequired[int]` + `state_schema=`.
- Tool nhận `run_context` rồi sửa `run_context.session_state` ↔ tool nhận `runtime: ToolRuntime`, trả
  `Command(update={...})`.
- `"{revision}"` trong instructions ↔ `@dynamic_prompt` đọc `request.state`, chạy trước MỖI lượt gọi model.
- Lưu theo `session_id` trong db ↔ lưu theo `thread_id` trong checkpointer.

Tham số `runtime` bị ẩn khỏi schema gửi cho model, giống `run_context` của Agno.
"""

from __future__ import annotations

from typing import Any, NotRequired

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt
from langchain.tools import ToolRuntime, tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ToolMessage
from langgraph.types import Checkpointer, Command


class DraftState(AgentState):
    revision: NotRequired[int]
    notes: NotRequired[list[str]]


@tool
def record_revision(note: str, runtime: ToolRuntime) -> Command:
    """Ghi nhận đã viết xong một phiên bản thư, kèm ghi chú ngắn về thay đổi. Chỉ gọi SAU khi đã viết xong."""
    revision = runtime.state.get("revision", 0) + 1
    notes = [*runtime.state.get("notes", []), f"v{revision}: {note}"]
    reply = ToolMessage(f"Đã ghi nhận phiên bản v{revision}", tool_call_id=runtime.tool_call_id)
    return Command(update={"revision": revision, "notes": notes, "messages": [reply]})


@dynamic_prompt
def revision_prompt(request: ModelRequest) -> str:
    return (
        "Bạn soạn thư cho khách hàng theo nhiều phiên bản trong cùng một phiên làm việc.\n"
        f"Phiên bản hiện tại: v{request.state.get('revision', 0)}. Viết xong một bản thì gọi record_revision."
    )


def build_state_agent(model: BaseChatModel, checkpointer: Checkpointer) -> Any:
    return create_agent(
        model,
        tools=[record_revision],
        state_schema=DraftState,
        middleware=[revision_prompt],
        checkpointer=checkpointer,
        name="draft-agent",
    )
