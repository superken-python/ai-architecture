"""Model offline cho OpenAI Agents SDK — chạy demo và test khi chưa có OPENAI_API_KEY.

Đọc câu cuối của người dùng bằng luật cố định (intent.py) rồi trả về đúng loại output mà model thật trả:
gọi handoff (agent điều phối), gọi tool (agent chuyên trách) hoặc tin nhắn văn bản. Dùng `ScriptedModel`
của SDK để dựng response/stream đúng chuẩn; mỗi lần gọi tạo một ScriptedModel mới nên không giữ trạng thái.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

from agents.models.interface import Model, ModelTracing
from agents.testing import ModelCall, ModelStep, ScriptedModel, assistant_message, function_call

from excel_agent.agents import intent
from excel_agent.agents.summaries import HELP_TEXT, summarize

OFFLINE_NOTE = "*(chế độ offline — chưa có `OPENAI_API_KEY`, câu được hiểu bằng luật cố định)*"


def _get(item: Any, key: str) -> Any:
    return item.get(key) if isinstance(item, dict) else getattr(item, key, None)


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(str(_get(part, "text") or "") for part in content)
    return ""


def _respond(call: ModelCall) -> list[Any]:
    items = call.input if isinstance(call.input, list) else [{"role": "user", "content": call.input}]
    last_user = max((i for i, it in enumerate(items) if _get(it, "role") == "user"), default=-1)
    user_text = _text(_get(items[last_user], "content")) if last_user >= 0 else ""
    after = items[last_user + 1 :]

    handoff_tools = {h.tool_name: h.agent_name for h in call.handoffs}
    called = {_get(it, "call_id"): _get(it, "name") for it in after if _get(it, "type") == "function_call"}
    outputs = [
        it
        for it in after
        if _get(it, "type") == "function_call_output"
        and not str(called.get(_get(it, "call_id"), "")).startswith("transfer_to")
    ]
    if outputs:  # tool đã chạy trong lượt này → trả lời tóm tắt
        return [assistant_message(f"{summarize(str(_get(outputs[-1], 'output')))}\n\n{OFFLINE_NOTE}")]

    kind = intent.detect_intent(user_text)
    if handoff_tools:  # agent điều phối: chọn agent chuyên trách
        wanted = "report" if kind == "report" else "search" if kind == "search" else None
        for tool_name, agent_name in handoff_tools.items():
            if wanted and wanted in agent_name.lower():
                return [function_call(tool_name, {}, call_id=f"call_{uuid.uuid4().hex[:12]}")]
        return [assistant_message(f"{HELP_TEXT}\n\n{OFFLINE_NOTE}")]

    tool_names = {t.name for t in call.tools}
    if kind == "report" and "export_excel" in tool_names:
        return [function_call("export_excel", intent.report_args(user_text), call_id=f"call_{uuid.uuid4().hex[:12]}")]
    if kind == "search" and "search_data" in tool_names:
        args = intent.search_args(user_text)
        if args["query"]:
            return [function_call("search_data", args, call_id=f"call_{uuid.uuid4().hex[:12]}")]
    return [assistant_message(f"{HELP_TEXT}\n\n{OFFLINE_NOTE}")]


class OfflineRuleModel(Model):
    """Thay thế OpenAIResponsesModel khi chạy không có API key."""

    async def get_response(
        self,
        system_instructions: str | None,
        input: Any,
        model_settings: Any,
        tools: list[Any],
        output_schema: Any,
        handoffs: list[Any],
        tracing: ModelTracing,
        *,
        previous_response_id: str | None = None,
        conversation_id: str | None = None,
        prompt: Any = None,
    ) -> Any:
        return await ScriptedModel([ModelStep.respond(_respond)]).get_response(
            system_instructions,
            input,
            model_settings,
            tools,
            output_schema,
            handoffs,
            tracing,
            previous_response_id=previous_response_id,
            conversation_id=conversation_id,
            prompt=prompt,
        )

    async def stream_response(  # type: ignore[override]
        self,
        system_instructions: str | None,
        input: Any,
        model_settings: Any,
        tools: list[Any],
        output_schema: Any,
        handoffs: list[Any],
        tracing: ModelTracing,
        *,
        previous_response_id: str | None = None,
        conversation_id: str | None = None,
        prompt: Any = None,
    ) -> AsyncIterator[Any]:
        model = ScriptedModel([ModelStep.respond(_respond)])
        async for event in model.stream_response(
            system_instructions,
            input,
            model_settings,
            tools,
            output_schema,
            handoffs,
            tracing,
            previous_response_id=previous_response_id,
            conversation_id=conversation_id,
            prompt=prompt,
        ):
            yield event
