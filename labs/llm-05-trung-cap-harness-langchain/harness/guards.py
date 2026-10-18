"""Guardrail, pre/post hook và model dự phòng — Agno Phần 8 ↔ middleware của LangChain.

- `pre_hooks` + `InputCheckError` ↔ `@before_agent(can_jump_to=["end"])` trả `{"jump_to": "end"}`.
  Cả hai không gọi model.
- `PIIDetectionGuardrail(mask_pii=True)` ↔ `PIIMiddleware("email", strategy="redact" | "mask")`.
  Agno che thành `***********`; LangChain thành `[REDACTED_EMAIL]` (redact) hoặc `lan@****.vn` (mask).
- `post_hooks` + `OutputCheckError` ↔ `@after_agent` trả message CÙNG `id` để ghi đè.
  Agno: status ERROR nhưng `content` vẫn là output vi phạm. LangChain: message vi phạm bị thay hẳn.
- `FallbackConfig(on_error=[model])` ↔ `ModelFallbackMiddleware(model)`.
  Cả hai không ghi lại model nào đã trả lời; cần thì tự ghi.
"""

from __future__ import annotations

import re
from typing import Any

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import ModelFallbackMiddleware, PIIMiddleware, after_agent, before_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from harness.data import CustomerDB
from harness.tools import make_server_tools

BLOCKED_URL = "[bị chặn] Câu trả lời chứa URL — không được dẫn nguồn web."


@before_agent(can_jump_to=["end"])
def require_customer_id(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Chặn TRƯỚC khi gọi model: yêu cầu phải nêu mã khách hàng."""
    if not re.search(r"KH-\d{4}", state["messages"][-1].text):
        return {"messages": [AIMessage("Yêu cầu phải nêu mã khách hàng dạng KH-0012.")], "jump_to": "end"}
    return None


@after_agent
def no_external_urls(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Kiểm tra SAU khi có câu trả lời: message mới cùng id thay message cũ (reducer add_messages)."""
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and re.search(r"https?://", last.text):
        return {"messages": [AIMessage(id=last.id, content=BLOCKED_URL)]}
    return None


def build_guarded_agent(model: BaseChatModel, db: CustomerDB, *, fallback: BaseChatModel | None = None) -> Any:
    middleware: list[Any] = [
        require_customer_id,
        PIIMiddleware("email", strategy="redact", apply_to_input=True),  # model thấy [REDACTED_EMAIL]
        no_external_urls,
    ]
    if fallback is not None:
        middleware.append(ModelFallbackMiddleware(fallback))  # model chính lỗi → thử model này
    return create_agent(model, tools=make_server_tools(db)[:1], middleware=middleware, name="guarded-agent")
