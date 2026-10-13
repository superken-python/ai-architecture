"""OpenAI Responses API giả lập (`POST /v1/responses`, có stream SSE) — chạy trong cùng tiến trình.

Dùng cho hai việc, đều đi qua đúng đường code thật của Agno (`OpenAIResponses` → SDK `openai` → HTTP):
- **Chế độ offline** khi chưa có OPENAI_API_KEY: "model" là bộ luật cố định (`RuleBrain`).
- **Test**: "model" trả lần lượt các bước đã định (`ScriptBrain`) — mô phỏng gpt-5-mini gọi tool, không cần key.

Chỉ cài phần Agno dùng: output là tin nhắn văn bản và/hoặc lời gọi hàm; usage ước lượng theo số ký tự.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

BASE_URL = "http://offline-llm/v1"


@dataclass
class Text:
    text: str


@dataclass
class Call:
    name: str
    arguments: dict[str, Any]
    call_id: str = field(default_factory=lambda: f"call_{uuid.uuid4().hex[:16]}")


Output = Text | Call


class Brain(Protocol):
    def respond(self, request: dict[str, Any]) -> list[Output]: ...


def _item(output: Output) -> dict[str, Any]:
    if isinstance(output, Call):
        return {
            "type": "function_call",
            "id": f"fc_{uuid.uuid4().hex[:16]}",
            "call_id": output.call_id,
            "name": output.name,
            "arguments": json.dumps(output.arguments, ensure_ascii=False),
            "status": "completed",
        }
    return {
        "type": "message",
        "id": f"msg_{uuid.uuid4().hex[:16]}",
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": output.text, "annotations": []}],
    }


def _response(body: dict[str, Any], response_id: str, items: list[dict[str, Any]], status: str) -> dict[str, Any]:
    input_tokens = len(json.dumps(body, ensure_ascii=False)) // 4
    output_tokens = len(json.dumps(items, ensure_ascii=False)) // 4
    return {
        "id": response_id,
        "object": "response",
        "created_at": int(time.time()),
        "model": body.get("model", "offline"),
        "status": status,
        "output": items if status == "completed" else [],
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
        "usage": {
            "input_tokens": input_tokens,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens": output_tokens,
            "output_tokens_details": {"reasoning_tokens": 0},
            "total_tokens": input_tokens + output_tokens,
        },
    }


def _sse(event: dict[str, Any]) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


def _stream(body: dict[str, Any], response_id: str, items: list[dict[str, Any]]) -> Iterator[str]:
    seq = 0

    def ev(kind: str, **data: Any) -> str:
        nonlocal seq
        seq += 1
        return _sse({"type": kind, "sequence_number": seq, **data})

    yield ev("response.created", response=_response(body, response_id, items, "in_progress"))
    for index, item in enumerate(items):
        if item["type"] == "function_call":
            yield ev("response.output_item.added", output_index=index, item={**item, "arguments": ""})
            yield ev(
                "response.function_call_arguments.delta",
                item_id=item["id"],
                output_index=index,
                delta=item["arguments"],
            )
            yield ev("response.output_item.done", output_index=index, item=item)
            continue
        text = item["content"][0]["text"]
        yield ev("response.output_item.added", output_index=index, item={**item, "content": []})
        for start in range(0, len(text), 24):  # chia nhỏ để giao diện thấy chữ chạy như model thật
            yield ev(
                "response.output_text.delta",
                item_id=item["id"],
                output_index=index,
                content_index=0,
                delta=text[start : start + 24],
            )
        yield ev("response.output_item.done", output_index=index, item=item)
    yield ev("response.completed", response=_response(body, response_id, items, "completed"))


def _orphan_outputs(body: dict[str, Any]) -> list[str]:
    items = [i for i in body.get("input") or [] if isinstance(i, dict)]
    calls = {i.get("call_id") for i in items if i.get("type") == "function_call"}
    return [
        i.get("call_id") for i in items if i.get("type") == "function_call_output" and i.get("call_id") not in calls
    ]


def create_app(brain: Brain) -> FastAPI:
    app = FastAPI(title="Offline LLM — OpenAI Responses API giả lập", docs_url=None, redoc_url=None)

    @app.post("/v1/responses")
    async def create_response(request: Request) -> Any:
        body = await request.json()
        orphan = _orphan_outputs(body)
        if orphan:  # như OpenAI khi store=false: kết quả tool phải khớp một lời gọi hàm trong input
            message = f"No tool call found for function call output with call_id {orphan[0]}."
            return JSONResponse(
                status_code=400, content={"error": {"message": message, "type": "invalid_request_error"}}
            )
        items = [_item(o) for o in brain.respond(body)]
        response_id = f"resp_{uuid.uuid4().hex}"
        if body.get("stream"):
            return StreamingResponse(_stream(body, response_id, items), media_type="text/event-stream")
        return JSONResponse(_response(body, response_id, items, "completed"))

    return app


def http_client(brain: Brain) -> httpx.AsyncClient:
    """Client HTTP gọi thẳng vào app giả lập (không qua mạng) — truyền cho `OpenAIResponses(http_client=...)`."""
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(brain)), timeout=30)
