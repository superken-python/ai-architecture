"""Gọi agent như một server sẽ gọi: một tin nhắn mới, hoặc chạy tiếp run đang tạm dừng."""

from __future__ import annotations

from typing import Any

from langgraph.types import Command

from harness.context import AgentContext


def ask(agent: Any, text: str, *, thread: str = "t1", ctx: AgentContext | None = None) -> dict[str, Any]:
    """Một run mới trên thread. `thread` = threadId của AG-UI = session_id của Agno."""
    return agent.invoke(
        {"messages": [{"role": "user", "content": text}]},
        {"configurable": {"thread_id": thread}},
        context=ctx or AgentContext(user_id="u1"),
    )


def resume(agent: Any, value: Any, *, thread: str = "t1", ctx: AgentContext | None = None) -> dict[str, Any]:
    """Chạy tiếp run đang dừng ở interrupt(): kết quả tool client, hoặc quyết định duyệt {"decisions": [...]}."""
    return agent.invoke(
        Command(resume=value), {"configurable": {"thread_id": thread}}, context=ctx or AgentContext(user_id="u1")
    )


def pending(out: dict[str, Any]) -> list[Any]:
    """Các interrupt đang chờ (rỗng = run đã kết thúc)."""
    return [i.value for i in out.get("__interrupt__", [])]


def resume_all(agent: Any, out: dict[str, Any], results: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Model gọi nhiều tool client trong CÙNG một lượt → nhiều interrupt. Client trả kết quả theo tool_call_id;
    LangGraph nhận `Command(resume={interrupt_id: giá trị})`. Thiếu kết quả nào thì run vẫn dừng ở interrupt đó."""
    by_interrupt = {
        i.id: results[i.value["tool_call_id"]] for i in out["__interrupt__"] if i.value["tool_call_id"] in results
    }
    return resume(agent, by_interrupt, **kwargs)
