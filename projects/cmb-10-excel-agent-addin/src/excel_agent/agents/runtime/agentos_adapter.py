"""Adapter đưa agent OpenAI Agents SDK vào AgentOS (Agno) — để AgentOS lo AG-UI, session, lưu lịch sử.

Agno 3.1 có adapter sẵn cho Claude Agent SDK, LangGraph, DSPy… nhưng chưa có cho OpenAI Agents SDK, nên
POC tự viết một lớp mỏng theo hợp đồng `BaseExternalAgent`:
- `_arun_adapter_stream`: chạy `Runner.run_streamed`, đổi sự kiện của SDK sang sự kiện AgentOS
  (RunContent / ToolCallStarted / ToolCallCompleted); AgentOS đổi tiếp sang AG-UI
  (TEXT_MESSAGE_*, TOOL_CALL_START/ARGS/END, TOOL_CALL_RESULT).
- `_arun_adapter`: bản không stream (REST `/agents/{id}/runs` với stream=false).
Lệnh `/search`, `/datasets`, `/help` chạy bằng code, không gọi model.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from agents import Agent, RunConfig, Runner
from agno.agents.base import BaseExternalAgent
from agno.models.response import ToolExecution
from agno.run.agent import RunContentEvent, RunOutputEvent, ToolCallCompletedEvent, ToolCallStartedEvent

from excel_agent.agents.commands import Command, parse_command
from excel_agent.agents.context import UI_CONTEXT_KEY, AgentDeps, UiState
from excel_agent.agents.summaries import HELP_TEXT, summarize
from excel_agent.agents.tools import run_list_datasets, run_search_data
from excel_agent.core.text import find_name

log = logging.getLogger(__name__)
MAX_TOOL_HISTORY_CHARS = 1500  # kết quả tool cũ đưa lại vào ngữ cảnh: cắt ngắn để tiết kiệm token (EFF-03)


@dataclass
class OpenAIAgentsAdapter(BaseExternalAgent):
    """Bọc một `agents.Agent` (OpenAI Agents SDK) thành agent của AgentOS."""

    starting_agent: Any = None  # agents.Agent[AgentDeps]
    deps_factory: Callable[[UiState], AgentDeps] | None = None
    max_turns: int = 8
    run_config: Any = None  # agents.RunConfig
    max_history_messages: int = 20

    _sdk_name: ClassVar[str] = "openai-agents"

    # ------------------------------------------------------------------ hợp đồng BaseExternalAgent
    async def _arun_adapter(self, input: Any, *, history: list[dict[str, Any]] | None = None, **kwargs: Any) -> str:
        deps = self._deps(kwargs)
        command = parse_command(_input_text(input))
        if command:
            _, text = await self._run_command(command, deps)
            return text
        try:
            result = await Runner.run(
                self._agent(),
                input=self._input_items(input, history),
                context=deps,
                max_turns=self.max_turns,
                run_config=self.run_config,
            )
        except Exception as exc:
            raise friendly_error(exc) from exc
        return str(result.final_output or "")

    async def _arun_adapter_stream(
        self, input: Any, *, history: list[dict[str, Any]] | None = None, **kwargs: Any
    ) -> AsyncIterator[RunOutputEvent]:
        run_id = kwargs.get("run_id") or str(uuid.uuid4())
        deps = self._deps(kwargs)
        command = parse_command(_input_text(input))
        if command:
            async for event in self._stream_command(command, deps, run_id):
                yield event
            return

        result = Runner.run_streamed(
            self._agent(),
            input=self._input_items(input, history),
            context=deps,
            max_turns=self.max_turns,
            run_config=self.run_config,
        )
        started: dict[str, str] = {}
        try:
            async for event in self._convert(result, run_id, started):
                yield event
        except Exception as exc:
            raise friendly_error(exc) from exc

    async def _convert(self, result: Any, run_id: str, started: dict[str, str]) -> AsyncIterator[RunOutputEvent]:
        """Đổi sự kiện stream của OpenAI Agents SDK sang sự kiện AgentOS."""
        async for event in result.stream_events():
            if event.type == "raw_response_event":
                data = event.data
                if getattr(data, "type", "") == "response.output_text.delta" and getattr(data, "delta", ""):
                    yield self._content(run_id, data.delta)
            elif event.type == "run_item_stream_event":
                item = event.item
                if event.name in ("tool_called", "handoff_requested"):
                    raw = item.raw_item
                    call_id = str(_get(raw, "call_id") or uuid.uuid4())
                    name = str(_get(raw, "name") or "tool")
                    started[call_id] = name
                    yield self._tool_started(run_id, call_id, name, _parse_args(_get(raw, "arguments")))
                elif event.name == "tool_output":
                    call_id = str(_get(item.raw_item, "call_id") or "")
                    yield self._tool_completed(run_id, call_id, started.get(call_id, "tool"), _as_text(item.output))
                elif event.name == "handoff_occured":
                    call_id = str(_get(item.raw_item, "call_id") or "")
                    target = getattr(getattr(item, "target_agent", None), "name", "")
                    payload = json.dumps({"type": "handoff", "to": target}, ensure_ascii=False)
                    yield self._tool_completed(run_id, call_id, started.get(call_id, "handoff"), payload)

    # ------------------------------------------------------------------ lệnh "/"
    async def _run_command(self, command: Command, deps: AgentDeps) -> tuple[str | None, str]:
        """Trả về (kết quả tool dạng JSON hoặc None, câu trả lời)."""
        if command.name == "help":
            return None, HELP_TEXT
        if command.name == "datasets":
            raw = await run_list_datasets(deps)
            return raw, summarize(raw)
        if command.name == "unknown":
            return None, f"Không có lệnh /{command.query}.\n\n{HELP_TEXT}"
        if not command.query:
            return None, "Gõ từ khóa sau /search, ví dụ `/search Đà Nẵng` hoặc `/search Thành phố: Đà Nẵng`."
        column, query = command.column, command.query
        if column:
            dataset = command.dataset or deps.active_dataset() or deps.settings.default_dataset
            info = next((d for d in await deps.datasets() if d["name"] == dataset), None)
            if info is None or find_name([c["name"] for c in info["columns"]], column) is None:
                query, column = f"{column}: {query}", None  # phần trước dấu ":" không phải tên cột
        raw = await run_search_data(deps, query, column, command.dataset)
        return raw, summarize(raw)

    async def _stream_command(self, command: Command, deps: AgentDeps, run_id: str) -> AsyncIterator[RunOutputEvent]:
        tool_name = {"search": "search_data", "datasets": "list_datasets"}.get(command.name)
        call_id = f"cmd_{uuid.uuid4().hex[:12]}"
        if tool_name:
            args = {"query": command.query, "column": command.column, "dataset": command.dataset}
            yield self._tool_started(run_id, call_id, tool_name, args if tool_name == "search_data" else {})
        raw, text = await self._run_command(command, deps)
        if tool_name:
            yield self._tool_completed(run_id, call_id, tool_name, raw or "null")
        yield self._content(run_id, text)

    # ------------------------------------------------------------------ tiện ích
    def _agent(self) -> Agent[AgentDeps]:
        if self.starting_agent is None:
            raise ValueError("OpenAIAgentsAdapter cần starting_agent")
        return self.starting_agent

    def _deps(self, kwargs: dict[str, Any]) -> AgentDeps:
        if self.deps_factory is None:
            raise ValueError("OpenAIAgentsAdapter cần deps_factory")
        run_context = kwargs.get("run_context")
        dependencies = getattr(run_context, "dependencies", None) or kwargs.get("dependencies") or {}
        return self.deps_factory(UiState.from_context(dependencies.get(UI_CONTEXT_KEY)))

    def _input_items(self, input: Any, history: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        """Lịch sử từ AgentOS (user / assistant / tool) → input của Responses API, kèm câu hỏi hiện tại."""
        items: list[dict[str, Any]] = []
        for msg in (history or [])[-self.max_history_messages :]:
            role, content = msg.get("role"), str(msg.get("content") or "")
            if role == "user" and content:
                items.append({"role": "user", "content": content})
            elif role == "assistant" and content:
                items.append({"role": "assistant", "content": content})
            elif role == "tool" and content:
                # giữ lại mã workbook / kết quả tìm kiếm cũ ở dạng tóm tắt để agent nhớ ngữ cảnh
                note = content[:MAX_TOOL_HISTORY_CHARS]
                items.append({"role": "assistant", "content": f"[kết quả công cụ trước đó] {note}"})
        items.append({"role": "user", "content": _input_text(input)})
        return items

    def _content(self, run_id: str, text: str) -> RunContentEvent:
        return RunContentEvent(run_id=run_id, agent_id=self.get_id(), agent_name=self.name or "", content=text)

    def _tool_started(self, run_id: str, call_id: str, name: str, args: dict[str, Any]) -> ToolCallStartedEvent:
        return ToolCallStartedEvent(
            run_id=run_id,
            agent_id=self.get_id(),
            agent_name=self.name or "",
            tool=ToolExecution(tool_call_id=call_id, tool_name=name, tool_args=args),
        )

    def _tool_completed(self, run_id: str, call_id: str, name: str, result: str) -> ToolCallCompletedEvent:
        return ToolCallCompletedEvent(
            run_id=run_id,
            agent_id=self.get_id(),
            agent_name=self.name or "",
            tool=ToolExecution(tool_call_id=call_id, tool_name=name, result=result),
        )


def friendly_error(exc: Exception) -> Exception:
    """Lỗi từ OpenAI → thông báo tiếng Việt có hướng xử lý (hiện trên giao diện qua sự kiện RUN_ERROR)."""
    import openai
    from agents.exceptions import MaxTurnsExceeded

    log.exception("Lỗi khi chạy agent")
    if isinstance(exc, openai.AuthenticationError):
        return RuntimeError(
            "OPENAI_API_KEY không hợp lệ hoặc đã bị thu hồi — kiểm tra file .env rồi khởi động lại server."
        )
    if isinstance(exc, openai.PermissionDeniedError | openai.NotFoundError):
        return RuntimeError(f"Key hiện tại không dùng được model đã cấu hình (OPENAI_MODEL): {exc}")
    if isinstance(exc, openai.RateLimitError):
        return RuntimeError("OpenAI báo vượt hạn mức (rate limit / hết credit) — thử lại sau hoặc kiểm tra billing.")
    if isinstance(exc, openai.APIConnectionError):
        return RuntimeError(
            "Không kết nối được OpenAI API — kiểm tra mạng, proxy hoặc OPENAI_BASE_URL. "
            "Lệnh /search, /datasets vẫn dùng được vì không cần model."
        )
    if isinstance(exc, MaxTurnsExceeded):
        return RuntimeError("Agent chạy quá số bước cho phép (MAX_TURNS) — hãy nói rõ yêu cầu hơn.")
    return exc


def build_run_config(workflow_name: str, tracing_disabled: bool) -> RunConfig:
    return RunConfig(workflow_name=workflow_name, tracing_disabled=tracing_disabled)


def _get(obj: Any, key: str) -> Any:
    return obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None)


def _parse_args(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw or "{}")
    except (json.JSONDecodeError, TypeError):
        return {"raw": str(raw)}
    return value if isinstance(value, dict) else {"value": value}


def _as_text(output: Any) -> str:
    if isinstance(output, str):
        return output
    try:
        return json.dumps(output, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(output)


def _input_text(input: Any) -> str:
    if isinstance(input, str):
        return input
    if isinstance(input, list):
        return " ".join(_input_text(part) for part in input)
    if isinstance(input, dict):
        return str(input.get("content") or input.get("text") or "")
    return str(input or "")
