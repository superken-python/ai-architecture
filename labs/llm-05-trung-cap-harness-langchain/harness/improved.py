"""Cải tiến harness theo cách Claude Code làm — mỗi lớp là một middleware độc lập, bật/tắt được.

| Claude Code                               | Middleware ở đây                                   |
|-------------------------------------------|----------------------------------------------------|
| CLAUDE.md nạp mỗi session                 | RulesFileMiddleware                                |
| Edit chỉ chạy khi file đã Read, chưa đổi  | ReadBeforeWriteMiddleware                          |
| Chạy test sau khi sửa                     | VerifyAfterWriteMiddleware                         |
| <system-reminder> chèn vào lượt user      | ReminderMiddleware                                 |
| Permission rules / chế độ quyền           | ToolPolicyMiddleware (+ HumanInTheLoopMiddleware)  |
| Tóm tắt khi hội thoại dài, xoá kết quả cũ | SummarizationMiddleware, ContextEditingMiddleware  |
| Danh sách việc (todo)                     | TodoListMiddleware                                 |
| Subagent ngữ cảnh riêng, chỉ trả kết quả  | make_subagent_tool                                 |
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import Annotated, Any, NotRequired

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ClearToolUsesEdit,
    ContextEditingMiddleware,
    ModelRequest,
    ModelResponse,
    SummarizationMiddleware,
    TodoListMiddleware,
    ToolCallRequest,
)
from langchain.tools import BaseTool, tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer, Command

from harness.agent import build_agent
from harness.data import CustomerDB

ToolHandler = Callable[[ToolCallRequest], ToolMessage | Command]
AsyncToolHandler = Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]]


def _blocked(request: ToolCallRequest, text: str) -> ToolMessage:
    return ToolMessage(
        content=text, tool_call_id=request.tool_call["id"], name=request.tool_call["name"], status="error"
    )


def _append_system(request: ModelRequest, block: str) -> ModelRequest:
    base = request.system_message.text if request.system_message else ""
    return request.override(system_message=SystemMessage(content=f"{base}\n\n{block}" if base else block))


class _ModelMiddleware(AgentMiddleware):
    """Khung chung: lớp con chỉ viết `_prepare`, có sẵn cả bản sync và async."""

    def _prepare(self, request: ModelRequest) -> ModelRequest:
        return request

    def wrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
        return handler(self._prepare(request))

    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable[ModelResponse]]
    ) -> ModelResponse:
        return await handler(self._prepare(request))


# ---------------------------------------------------------------- 1. File luật dự án (CLAUDE.md)
class RulesFileMiddleware(_ModelMiddleware):
    """Nối nội dung file luật vào system prompt. Đọc lại khi file đổi — người sửa file, agent theo ngay."""

    def __init__(self, path: str | Path) -> None:
        super().__init__()
        self.path = Path(path)
        self._cache: tuple[float, str] | None = None

    def rules(self) -> str:
        mtime = self.path.stat().st_mtime
        if self._cache is None or self._cache[0] != mtime:
            self._cache = (mtime, self.path.read_text(encoding="utf-8").strip())
        return self._cache[1]

    def _prepare(self, request: ModelRequest) -> ModelRequest:
        return _append_system(request, f"<project_rules>\n{self.rules()}\n</project_rules>")


# ---------------------------------------------------------------- 2. Đọc trước khi ghi
def _merge(old: dict[str, str] | None, new: dict[str, str] | None) -> dict[str, str]:
    return {**(old or {}), **(new or {})}


class ReadTrackingState(AgentState):
    read_versions: NotRequired[Annotated[dict[str, str], _merge]]


class ReadBeforeWriteMiddleware(AgentMiddleware):
    """Chặn ghi vào bản ghi chưa đọc, hoặc đã bị đổi sau lần đọc (giống Edit của Claude Code).

    reads:  tool đọc → hàm (args, kết quả) trả các khóa đã đọc
    writes: tool ghi → hàm (args) trả khóa sẽ ghi
    fingerprint: khóa → dấu vân tay dữ liệu hiện tại (None nếu không có)
    """

    state_schema = ReadTrackingState

    def __init__(
        self,
        *,
        reads: dict[str, Callable[[dict, str], list[str]]],
        writes: dict[str, Callable[[dict], str]],
        fingerprint: Callable[[str], str | None],
    ) -> None:
        super().__init__()
        self.reads, self.writes, self.fingerprint = reads, writes, fingerprint

    def _check_write(self, request: ToolCallRequest) -> ToolMessage | None:
        key = self.writes[request.tool_call["name"]](request.tool_call["args"])
        seen = (request.state.get("read_versions") or {}).get(key)
        if seen is None:
            return _blocked(
                request, f"Chặn: chưa đọc {key} trong cuộc trò chuyện này. Đọc dữ liệu hiện tại trước khi ghi."
            )
        if seen != self.fingerprint(key):
            return _blocked(request, f"Chặn: {key} đã thay đổi sau lần đọc trước. Đọc lại rồi mới ghi.")
        return None

    def _after(self, request: ToolCallRequest, result: ToolMessage | Command) -> ToolMessage | Command:
        name = request.tool_call["name"]
        if not isinstance(result, ToolMessage) or result.status == "error":
            return result
        if name in self.reads:
            keys = self.reads[name](request.tool_call["args"], result.text)
        elif name in self.writes:
            keys = [self.writes[name](request.tool_call["args"])]  # ghi xong thì bản mới coi như đã đọc
        else:
            return result
        versions = {k: v for k in keys if (v := self.fingerprint(k)) is not None}
        return Command(update={"messages": [result], "read_versions": versions}) if versions else result

    def wrap_tool_call(self, request: ToolCallRequest, handler: ToolHandler) -> ToolMessage | Command:
        if request.tool_call["name"] in self.writes and (blocked := self._check_write(request)):
            return blocked
        return self._after(request, handler(request))

    async def awrap_tool_call(self, request: ToolCallRequest, handler: AsyncToolHandler) -> ToolMessage | Command:
        if request.tool_call["name"] in self.writes and (blocked := self._check_write(request)):
            return blocked
        return self._after(request, await handler(request))


# ---------------------------------------------------------------- 3. Kiểm chứng sau khi ghi
class VerifyAfterWriteMiddleware(AgentMiddleware):
    """Sau khi tool ghi chạy xong, đọc lại nguồn và nối kết quả kiểm tra vào ToolMessage — model thấy ngay nếu sai."""

    def __init__(self, verifiers: dict[str, Callable[[dict], str | None]]) -> None:
        super().__init__()
        self.verifiers = verifiers  # trả None nếu đúng, chuỗi mô tả lỗi nếu sai

    def _verify(self, request: ToolCallRequest, result: ToolMessage | Command) -> ToolMessage | Command:
        verify = self.verifiers.get(request.tool_call["name"])
        if verify is None or not isinstance(result, ToolMessage) or result.status == "error":
            return result
        problem = verify(request.tool_call["args"])
        note = "Kiểm tra lại: OK, dữ liệu nguồn khớp." if problem is None else f"Kiểm tra lại: SAI — {problem}"
        return result.model_copy(update={"content": f"{result.text}\n{note}"})

    def wrap_tool_call(self, request: ToolCallRequest, handler: ToolHandler) -> ToolMessage | Command:
        return self._verify(request, handler(request))

    async def awrap_tool_call(self, request: ToolCallRequest, handler: AsyncToolHandler) -> ToolMessage | Command:
        return self._verify(request, await handler(request))


# ---------------------------------------------------------------- 4. Nhắc trạng thái (system-reminder)
def default_reminder(request: ModelRequest) -> str | None:
    starts = [i for i, m in enumerate(request.messages) if isinstance(m, HumanMessage)]
    run = request.messages[starts[-1] :] if starts else request.messages
    used = sum(1 for m in run if isinstance(m, ToolMessage))
    return f"Hôm nay {dt.date.today().isoformat()}. Yêu cầu hiện tại đã dùng {used} lượt tool."


class ReminderMiddleware(_ModelMiddleware):
    """Chèn một tin nhắn <system-reminder> vào CUỐI messages của lần gọi model (không lưu vào state).

    Đặt ở cuối thay vì sửa system prompt để giữ nguyên phần đầu ngữ cảnh → prompt cache vẫn trúng.
    """

    def __init__(self, make: Callable[[ModelRequest], str | None] = default_reminder) -> None:
        super().__init__()
        self.make = make

    def _prepare(self, request: ModelRequest) -> ModelRequest:
        text = self.make(request)
        if not text:
            return request
        return request.override(
            messages=[*request.messages, HumanMessage(content=f"<system-reminder>{text}</system-reminder>")]
        )


# ---------------------------------------------------------------- 5. Chính sách quyền
class ToolPolicyMiddleware(AgentMiddleware):
    """Chặn tool theo quyền của người dùng (runtime.context.role) — chạy trước khi tool chạy."""

    def __init__(self, deny_by_role: dict[str, set[str]]) -> None:
        super().__init__()
        self.deny_by_role = deny_by_role

    def _check(self, request: ToolCallRequest) -> ToolMessage | None:
        role = getattr(request.runtime.context, "role", None)
        if request.tool_call["name"] in self.deny_by_role.get(role, set()):
            return _blocked(
                request,
                f"Không được phép: vai trò '{role}' không dùng được {request.tool_call['name']}. Báo người dùng.",
            )
        return None

    def wrap_tool_call(self, request: ToolCallRequest, handler: ToolHandler) -> ToolMessage | Command:
        return self._check(request) or handler(request)

    async def awrap_tool_call(self, request: ToolCallRequest, handler: AsyncToolHandler) -> ToolMessage | Command:
        return self._check(request) or await handler(request)


# ---------------------------------------------------------------- 6. Subagent
def make_subagent_tool(
    name: str, description: str, model: BaseChatModel, tools: Sequence[BaseTool], system_prompt: str
) -> BaseTool:
    """Một agent con chạy với ngữ cảnh riêng; agent chính chỉ nhận câu trả lời cuối (không nhận các bước giữa)."""
    sub = create_agent(model, tools=list(tools), system_prompt=system_prompt, checkpointer=False, name=name)

    @tool(name, description=description)
    def run_subagent(task: str) -> str:
        out = sub.invoke({"messages": [HumanMessage(content=task)]})
        final = next((m for m in reversed(out["messages"]) if isinstance(m, AIMessage) and not m.tool_calls), None)
        return final.text if final else "(agent con không trả lời)"

    return run_subagent


# ---------------------------------------------------------------- Ráp lại cho bài toán khách hàng
def customer_guards(db: CustomerDB) -> list[AgentMiddleware]:
    def fingerprint(key: str) -> str | None:
        row = db.get(key)
        return (
            hashlib.sha1(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12] if row else None
        )

    def read_ids(args: dict, result: str) -> list[str]:
        try:
            return [row["id"] for row in json.loads(result)]
        except (json.JSONDecodeError, TypeError, KeyError):
            return []  # kết quả lỗi / không tìm thấy → không có gì được coi là đã đọc

    def verify_update(args: dict) -> str | None:
        row = db.get(args["customer_id"])
        if row is None:
            return f"không còn khách hàng {args['customer_id']}"
        if str(row.get(args["field"])) != str(args["value"]):
            return f"{args['field']} hiện là {row.get(args['field'])!r}, không phải {args['value']!r}"
        return None

    return [
        ToolPolicyMiddleware({"viewer": {"update_customer", "excel_set_values"}}),
        ReadBeforeWriteMiddleware(
            reads={"search_customers": read_ids},
            writes={"update_customer": lambda args: args["customer_id"]},
            fingerprint=fingerprint,
        ),
        VerifyAfterWriteMiddleware({"update_customer": verify_update}),
    ]


def build_improved_agent(
    model: BaseChatModel,
    *,
    db: CustomerDB,
    checkpointer: Checkpointer,
    store: BaseStore | None = None,
    memory_model: BaseChatModel | None = None,
    summary_model: BaseChatModel | None = None,
    rules_path: str | Path | None = None,
    subagents: Sequence[BaseTool] = (),
    todo: bool = False,
    reminders: bool = True,
    **kwargs: Any,
):
    extra: list[AgentMiddleware] = []
    if rules_path is not None:
        extra.append(RulesFileMiddleware(rules_path))
    if summary_model is not None:
        # Hội thoại dài: tóm tắt phần cũ (ghi đè state), giữ 20 tin nhắn cuối.
        extra.append(SummarizationMiddleware(summary_model, trigger=("tokens", 8000), keep=("messages", 20)))
    # Kết quả tool cũ chiếm nhiều token nhất: thay bằng "[cleared]" khi ngữ cảnh vượt ngưỡng, giữ 3 kết quả gần nhất.
    extra.append(ContextEditingMiddleware(edits=[ClearToolUsesEdit(trigger=6000, keep=3)]))
    if todo:
        extra.append(TodoListMiddleware())
    extra.extend(customer_guards(db))
    if reminders:
        extra.append(ReminderMiddleware())
    return build_agent(
        model,
        db=db,
        checkpointer=checkpointer,
        store=store,
        memory_model=memory_model,
        extra_tools=subagents,
        extra_middleware=extra,
        **kwargs,
    )
