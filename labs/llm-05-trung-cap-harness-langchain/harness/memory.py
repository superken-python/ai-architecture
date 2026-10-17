"""Memory dài hạn theo user — tương đương `update_memory_on_run` + `add_memories_to_context` của Agno.

Hai nửa:
1. Đọc (mỗi lần gọi model): lấy memory của `user_id` từ store, nối vào cuối system prompt — giống Agno.
2. Ghi (một lần, khi run kết thúc — hook `after_agent`): chạy một agent nhỏ có tool add/update/delete_memory,
   đọc tin nhắn user của run vừa xong và quyết định ghi gì — giống MemoryManager của Agno.

Khác Agno, có chủ ý:
- `user_id` là None → không đọc, không ghi (Agno gom mọi người ẩn danh vào user "default").
- Ghi ở cuối run, tuần tự (Agno chạy song song với lượt model chính rồi chờ). Run bị interrupt thì chưa ghi;
  ghi khi run được resume và kết thúc.
- `include_assistant=True` cho trình trích xuất thấy cả câu trả lời cuối (Agno chỉ thấy tin nhắn user).
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse, ToolCallLimitMiddleware
from langchain.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore

MEMORY_PROMPT = """Bạn quản lý trí nhớ dài hạn về NGƯỜI DÙNG (không phải dữ liệu nghiệp vụ).
Đọc đoạn hội thoại và quyết định:
- add_memory: thêm thông tin ổn định, có ích về người dùng (tên, vai trò, khu vực phụ trách, cách làm việc quen).
- update_memory: sửa một memory đã có khi thông tin mới thay đổi nó.
- delete_memory: xóa memory sai, hoặc khi người dùng yêu cầu quên.
KHÔNG lưu: số liệu khách hàng, mã giao dịch, kết quả tra cứu, yêu cầu tạm thời.
Không có gì đáng nhớ thì trả lời "không có" và không gọi tool.

<existing_memories>
{existing}
</existing_memories>"""

CONTEXT_BLOCK = """Thông tin về người dùng từ các lần trước.
Nếu mâu thuẫn, ưu tiên thông tin trong cuộc trò chuyện hiện tại.
<memories_from_previous_interactions>
{items}
</memories_from_previous_interactions>"""

MAX_MEMORIES = 100  # store.search mặc định chỉ trả 10


def _user_id(runtime: Any) -> str | None:
    return getattr(runtime.context, "user_id", None)


def _text(message: AnyMessage | None) -> str:
    return message.text if message is not None else ""


class UserMemoryMiddleware(AgentMiddleware):
    def __init__(
        self,
        extractor_model: BaseChatModel,
        *,
        inject: bool = True,
        extract: bool = True,
        include_assistant: bool = False,
        namespace: str = "memories",
    ) -> None:
        super().__init__()
        self.extractor_model = extractor_model
        self.inject, self.extract, self.include_assistant = inject, extract, include_assistant
        self.namespace = namespace

    def ns(self, user_id: str) -> tuple[str, str]:
        return (self.namespace, user_id)

    def list(self, store: BaseStore, user_id: str) -> list[Any]:
        return store.search(self.ns(user_id), limit=MAX_MEMORIES)

    # ---------- 1. Đọc: nối memory vào system prompt trước mỗi lần gọi model ----------
    def _prepare(self, request: ModelRequest) -> ModelRequest:
        user_id, store = _user_id(request.runtime), request.runtime.store
        if not (self.inject and user_id and store):
            return request
        items = self.list(store, user_id)
        if not items:
            return request
        block = CONTEXT_BLOCK.format(items="\n".join(f"- {it.value['memory']}" for it in items))
        base = _text(request.system_message)
        return request.override(system_message=SystemMessage(content=f"{base}\n\n{block}" if base else block))

    def wrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
        return handler(self._prepare(request))

    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable[ModelResponse]]
    ) -> ModelResponse:
        return await handler(self._prepare(request))

    # ---------- 2. Ghi: khi run kết thúc ----------
    def extraction_input(self, messages: list[AnyMessage]) -> HumanMessage | None:
        starts = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
        if not starts:
            return None
        run = messages[starts[-1] :]
        lines = [f"Người dùng: {_text(run[0])}"]
        if self.include_assistant:
            final = next((m for m in reversed(run) if isinstance(m, AIMessage) and not m.tool_calls), None)
            if final is not None:
                lines.append(f"Trợ lý: {_text(final)}")
        return HumanMessage(content="\n".join(lines))

    def extractor(self, store: BaseStore, user_id: str):
        ns = self.ns(user_id)

        @tool
        def add_memory(memory: str, topics: list[str] | None = None) -> str:
            """Thêm một memory mới về người dùng."""
            key = uuid.uuid4().hex[:8]
            store.put(ns, key, {"memory": memory, "topics": topics or []})
            return f"Đã thêm memory {key}"

        @tool
        def update_memory(memory_id: str, memory: str) -> str:
            """Sửa nội dung một memory đã có (theo ID trong existing_memories)."""
            old = store.get(ns, memory_id)
            if old is None:
                return f"Không có memory {memory_id}. Dùng add_memory nếu là thông tin mới."
            store.put(ns, memory_id, {**old.value, "memory": memory})
            return f"Đã sửa memory {memory_id}"

        @tool
        def delete_memory(memory_id: str) -> str:
            """Xóa một memory (theo ID trong existing_memories)."""
            store.delete(ns, memory_id)
            return f"Đã xóa memory {memory_id}"

        existing = "\n".join(f"ID: {it.key} | {it.value['memory']}" for it in self.list(store, user_id)) or "(chưa có)"
        return create_agent(
            self.extractor_model,
            tools=[add_memory, update_memory, delete_memory],
            system_prompt=MEMORY_PROMPT.format(existing=existing),
            middleware=[ToolCallLimitMiddleware(run_limit=5, exit_behavior="end")],
            checkpointer=False,  # không lưu hội thoại của trình trích xuất vào checkpointer của agent chính
            name="memory-extractor",
        )

    def _job(self, state: dict[str, Any], runtime: Runtime) -> tuple[Any, HumanMessage] | None:
        user_id, store = _user_id(runtime), runtime.store
        if not (self.extract and user_id and store):
            return None
        message = self.extraction_input(state["messages"])
        return (self.extractor(store, user_id), message) if message is not None else None

    def after_agent(self, state: dict[str, Any], runtime: Runtime) -> dict[str, Any] | None:
        job = self._job(state, runtime)
        if job:
            job[0].invoke({"messages": [job[1]]})
        return None

    async def aafter_agent(self, state: dict[str, Any], runtime: Runtime) -> dict[str, Any] | None:
        job = self._job(state, runtime)
        if job:
            await job[0].ainvoke({"messages": [job[1]]})
        return None
