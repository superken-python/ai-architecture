"""Ráp harness: model + tools + instructions + lịch sử + memory + giới hạn + người duyệt.

Thứ tự middleware quan trọng: với wrap_model_call, middleware ĐỨNG TRƯỚC là lớp NGOÀI và chạy trước.
`instructions` (đặt system prompt) phải đứng trước mọi middleware nối thêm vào system prompt (memory, rules, ...).
"""

from __future__ import annotations

from collections.abc import Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    HumanInTheLoopMiddleware,
    ModelCallLimitMiddleware,
    ToolCallLimitMiddleware,
)
from langchain.tools import BaseTool
from langchain_core.language_models import BaseChatModel
from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer

from harness.context import AgentContext
from harness.data import CustomerDB
from harness.history import HistoryWindowMiddleware
from harness.instructions import instructions
from harness.memory import UserMemoryMiddleware
from harness.tools import CLIENT_TOOLS, make_server_tools


def build_agent(
    model: BaseChatModel,
    *,
    db: CustomerDB,
    checkpointer: Checkpointer,
    store: BaseStore | None = None,
    memory_model: BaseChatModel | None = None,
    num_history_runs: int = 3,
    tool_call_limit: int = 8,
    model_call_limit: int = 15,
    limit_exit: str = "end",
    approve_writes: bool = True,
    client_tools: bool = True,
    extra_tools: Sequence[BaseTool] = (),
    extra_middleware: Sequence[AgentMiddleware] = (),
):
    tools = [*make_server_tools(db), *(CLIENT_TOOLS if client_tools else []), *extra_tools]
    middleware: list[AgentMiddleware] = [
        # Agno: tool_call_limit chỉ chặn từng lượt gọi, vòng lặp vẫn chạy. Ở đây dừng hẳn ("end") và có thêm trần
        # số lượt gọi model — guard mà Agno không có.
        ModelCallLimitMiddleware(run_limit=model_call_limit, exit_behavior="end"),
        ToolCallLimitMiddleware(run_limit=tool_call_limit, exit_behavior=limit_exit),
        instructions,
        HistoryWindowMiddleware(num_history_runs),
    ]
    if memory_model is not None:
        middleware.append(UserMemoryMiddleware(memory_model))
    if approve_writes:
        # Agno: requires_confirmation=True trên tool
        middleware.append(
            HumanInTheLoopMiddleware(interrupt_on={"update_customer": {"allowed_decisions": ["approve", "reject"]}})
        )
    middleware.extend(extra_middleware)
    return create_agent(
        model,
        tools=tools,
        middleware=middleware,
        context_schema=AgentContext,
        checkpointer=checkpointer,
        store=store,
        name="excel-agent",
    )
