"""Model cho harness: model thật (OpenAI hoặc endpoint tương thích OpenAI) và model kịch bản để test.

Model kịch bản đóng vai `ScriptBrain` của CMB-10: mỗi lần được gọi trả về bước kế tiếp đã định sẵn và ghi lại
toàn bộ messages + tên tool nó nhận được, để test kiểm tra harness đã đưa gì cho model.
"""

from __future__ import annotations

import uuid
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


def build_model(model: str = "gpt-5-mini", *, base_url: str | None = None, api_key: str | None = None) -> BaseChatModel:
    """Model thật. `base_url` trỏ tới vLLM / llama.cpp / Ollama (đều có API tương thích OpenAI) nếu chạy local.

    Cần `pip install langchain-openai`. Chưa chạy thử với API thật trong lab này (môi trường không có key).
    """
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {"model": model}
    if base_url:
        kwargs["base_url"] = base_url  # endpoint local thường chỉ có Chat Completions
    else:
        kwargs["use_responses_api"] = True  # OpenAI: Responses API
    if api_key:
        kwargs["api_key"] = api_key
    return ChatOpenAI(**kwargs)


def say(text: str) -> AIMessage:
    """Bước kịch bản: model trả lời bằng chữ, không gọi tool → vòng lặp dừng."""
    return AIMessage(content=text)


def call(name: str, **args: Any) -> AIMessage:
    """Bước kịch bản: model gọi một tool."""
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:12]}"}])


class ScriptedChatModel(BaseChatModel):
    """Model giả: trả lần lượt `steps`, ghi lại input của từng lần gọi."""

    steps: list[AIMessage]
    calls: list[list[BaseMessage]] = Field(default_factory=list)
    bound_tools: list[list[str]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Any, **kwargs: Any) -> ScriptedChatModel:
        self.bound_tools.append([getattr(t, "name", None) or t.get("name", "?") for t in tools])
        return self

    def _generate(self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any):
        self.calls.append(list(messages))
        if len(self.calls) > len(self.steps):
            raise AssertionError(f"Model được gọi lần {len(self.calls)} nhưng kịch bản chỉ có {len(self.steps)} bước")
        step = self.steps[len(self.calls) - 1]
        return ChatResult(generations=[ChatGeneration(message=step.model_copy(deep=True))])
