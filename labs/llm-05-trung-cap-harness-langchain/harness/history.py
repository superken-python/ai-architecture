"""Cửa sổ lịch sử theo số run — tương đương `add_history_to_context` + `num_history_runs` của Agno.

Khác biệt cần nhớ:
- Agno lưu từng run thành một dòng DB rồi lấy N run gần nhất. LangGraph lưu CẢ thread trong state (checkpointer),
  nên ở đây ta chỉ cắt phần MODEL NHÌN THẤY; state vẫn giữ đủ. Muốn state không phình, thêm SummarizationMiddleware.
- "Một run" = từ một HumanMessage tới trước HumanMessage kế tiếp (gồm tool call, kết quả tool, câu trả lời).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import AnyMessage, HumanMessage


def window(messages: list[AnyMessage], num_history_runs: int) -> list[AnyMessage]:
    """Giữ N run trước + run hiện tại (run hiện tại bắt đầu ở HumanMessage cuối)."""
    starts = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
    if len(starts) <= num_history_runs + 1:
        return messages
    return messages[starts[-(num_history_runs + 1)] :]


class HistoryWindowMiddleware(AgentMiddleware):
    def __init__(self, num_history_runs: int = 3) -> None:  # Agno mặc định 3
        super().__init__()
        self.num_history_runs = num_history_runs

    def _prepare(self, request: ModelRequest) -> ModelRequest:
        return request.override(messages=window(request.messages, self.num_history_runs))

    def wrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
        return handler(self._prepare(request))

    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable[ModelResponse]]
    ) -> ModelResponse:
        return await handler(self._prepare(request))
