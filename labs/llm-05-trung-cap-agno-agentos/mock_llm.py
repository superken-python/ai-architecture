"""Server giả lập API OpenAI: Chat Completions (thường + stream) và Embeddings — học Agno không cần API key.

    uv run python mock_llm.py                 # http://127.0.0.1:8900/v1, chế độ tự động
    # .env: OPENAI_BASE_URL=http://127.0.0.1:8900/v1  OPENAI_API_KEY=mock  MODEL_ID=mock

Hai chế độ trả lời:
- Kịch bản (test): nạp trước các bước bằng `MockLLM.script(...)`; mỗi request lấy bước kế tiếp của kênh khớp.
- Tự động (học offline): không có kịch bản thì request đòi JSON theo schema nhận JSON hợp lệ sinh từ schema,
  request thường nhận một câu mẫu. Không bao giờ tự gọi tool.

Mock không thông minh: nó chứng minh code nối đúng (tool được gọi, kết quả quay lại model, schema được validate),
KHÔNG chứng minh model thật chọn tool đúng — việc đó cần model thật và bộ eval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import socket
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse


# ---------------------------------------------------------------- bước kịch bản
@dataclass
class Step:
    text: str | None = None
    tool_calls: list[dict] | None = None  # [{"name": ..., "arguments": {...}}]


def say(text: str) -> Step:
    """Model trả lời bằng chữ (hoặc JSON dạng chuỗi) và không gọi tool → vòng lặp agent dừng."""
    return Step(text=text)


def answer_json(value: Any) -> Step:
    """Model trả JSON — dùng khi agent có output_schema."""
    return Step(text=json.dumps(value, ensure_ascii=False))


def call(name: str, **arguments: Any) -> Step:
    """Model gọi một tool."""
    return Step(tool_calls=[{"name": name, "arguments": arguments}])


def calls(*pairs: tuple[str, dict]) -> Step:
    """Model gọi nhiều tool trong cùng một lượt (song song)."""
    return Step(tool_calls=[{"name": n, "arguments": a} for n, a in pairs])


@dataclass
class Channel:
    match: str  # chuỗi phải có trong system prompt; "" = kênh mặc định
    steps: list[Step] = field(default_factory=list)
    used: int = 0


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(part.get("text", "") for part in content if isinstance(part, dict))
    return ""


def system_text(body: dict) -> str:
    return "\n".join(
        _text(m.get("content")) for m in body.get("messages", []) if m.get("role") in ("system", "developer")
    )


# ---------------------------------------------------------------- JSON mẫu từ schema (chế độ tự động)
def example_from_schema(schema: dict, defs: dict | None = None) -> Any:
    defs = defs if defs is not None else schema.get("$defs", {})
    if "$ref" in schema:
        return example_from_schema(defs[schema["$ref"].split("/")[-1]], defs)
    if "anyOf" in schema:
        options = [s for s in schema["anyOf"] if s.get("type") != "null"] or schema["anyOf"]
        return example_from_schema(options[0], defs)
    if "enum" in schema:
        return schema["enum"][0]
    kind = schema.get("type")
    if kind == "object":
        props = schema.get("properties", {})
        return {key: example_from_schema(sub, defs) for key, sub in props.items()}
    if kind == "array":
        count = max(1, schema.get("minItems", 1))
        return [example_from_schema(schema.get("items", {"type": "string"}), defs) for _ in range(count)]
    if kind == "integer":
        return 1
    if kind == "number":
        return 1.0
    if kind == "boolean":
        return True
    return "(mock) nội dung mẫu"


# ---------------------------------------------------------------- embeddings tất định
def embed(text: str, dims: int) -> list[float]:
    """Hashing trick: cùng từ → cùng chiều. Đủ để thấy câu chung từ khóa gần nhau; không phải semantic thật."""
    vector = [0.0] * dims
    for word in re.findall(r"\w+", text.lower()):
        digest = int(hashlib.md5(word.encode()).hexdigest(), 16)
        vector[digest % dims] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


# ---------------------------------------------------------------- server
class MockLLM:
    def __init__(self) -> None:
        self.channels: list[Channel] = []
        self.requests: list[dict] = []
        self.embedding_requests: list[dict] = []
        self._lock = threading.Lock()
        self.app = self._build_app()
        self.base_url: str | None = None

    # --- API cho test ---
    def script(self, *steps: Step, match: str = "") -> Channel:
        """Thêm bước cho kênh `match` (chuỗi có trong system prompt của agent cần trả lời)."""
        with self._lock:
            channel = next((c for c in self.channels if c.match == match), None)
            if channel is None:
                channel = Channel(match)
                # kênh có điều kiện được xét trước kênh mặc định
                self.channels.insert(0 if match else len(self.channels), channel)
            channel.steps.extend(steps)
            return channel

    def reset(self) -> None:
        with self._lock:
            self.channels.clear()
            self.requests.clear()
            self.embedding_requests.clear()

    def requests_for(self, match: str) -> list[dict]:
        return [r for r in self.requests if match in system_text(r)]

    def remaining(self) -> dict[str, int]:
        return {c.match or "<mặc định>": len(c.steps) - c.used for c in self.channels}

    # --- chọn câu trả lời ---
    def _next(self, body: dict) -> Step:
        with self._lock:
            self.requests.append(body)
            if not self.channels:
                return self._auto(body)
            sys_text = system_text(body)
            channel = next((c for c in self.channels if c.match and c.match in sys_text), None)
            channel = channel or next((c for c in self.channels if not c.match), None)
            if channel is None:
                raise RuntimeError(f"mock: không có kênh nào khớp system prompt: {sys_text[:200]!r}")
            if channel.used >= len(channel.steps):  # hết bước thì báo lỗi, không lấy bước của kênh khác
                raise RuntimeError(
                    f"mock: kịch bản kênh {channel.match or '<mặc định>'!r} đã hết ({channel.used} bước)"
                )
            channel.used += 1
            return channel.steps[channel.used - 1]

    @staticmethod
    def _auto(body: dict) -> Step:
        response_format = body.get("response_format") or {}
        if response_format.get("type") == "json_schema":
            return answer_json(example_from_schema(response_format["json_schema"]["schema"]))
        if response_format.get("type") == "json_object":
            return answer_json({"result": "(mock)"})
        last_user = next(
            (_text(m.get("content")) for m in reversed(body.get("messages", [])) if m.get("role") == "user"), ""
        )
        return say(f"(mock) Đã nhận: {last_user[:120]}")

    # --- định dạng OpenAI ---
    @staticmethod
    def _usage(body: dict, step: Step) -> dict:
        prompt = sum(len(_text(m.get("content")) or "") for m in body.get("messages", [])) // 4 + 1
        completion = len(step.text or json.dumps(step.tool_calls or [])) // 4 + 1
        return {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": prompt + completion}

    @staticmethod
    def _tool_calls(step: Step) -> list[dict]:
        return [
            {
                "id": f"call_{uuid.uuid4().hex[:16]}",
                "type": "function",
                "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"], ensure_ascii=False)},
            }
            for tc in step.tool_calls or []
        ]

    def _completion(self, body: dict, step: Step) -> dict:
        message: dict[str, Any] = {"role": "assistant", "content": step.text}
        tool_calls = self._tool_calls(step)
        if tool_calls:
            message["tool_calls"] = tool_calls
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": body.get("model", "mock"),
            "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if tool_calls else "stop"}],
            "usage": self._usage(body, step),
        }

    def _stream(self, body: dict, step: Step):
        base = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": body.get("model", "mock"),
        }

        def chunk(delta: dict, finish: str | None = None, **extra: Any) -> str:
            payload = {**base, "choices": [{"index": 0, "delta": delta, "finish_reason": finish}], **extra}
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        yield chunk({"role": "assistant", "content": ""})
        text = step.text or ""
        for i in range(0, len(text), 24):  # chia nhỏ để thấy token streaming
            yield chunk({"content": text[i : i + 24]})
        tool_calls = self._tool_calls(step)
        for index, tc in enumerate(tool_calls):
            yield chunk({"tool_calls": [{"index": index, **tc}]})
        yield chunk({}, "tool_calls" if tool_calls else "stop")
        if (body.get("stream_options") or {}).get("include_usage"):
            usage = {**base, "choices": [], "usage": self._usage(body, step)}
            yield f"data: {json.dumps(usage)}\n\n"
        yield "data: [DONE]\n\n"

    def _build_app(self) -> FastAPI:
        app = FastAPI(title="mock-openai", telemetry={"tracing": False})  # không trộn span của mock vào trace agent

        @app.post("/v1/chat/completions")
        async def chat(request: Request):
            body = await request.json()
            try:
                step = self._next(body)
            except RuntimeError as exc:
                return JSONResponse({"error": {"message": str(exc), "type": "mock_script"}}, status_code=500)
            if body.get("stream"):
                return StreamingResponse(self._stream(body, step), media_type="text/event-stream")
            return self._completion(body, step)

        @app.post("/v1/embeddings")
        async def embeddings(request: Request):
            body = await request.json()
            self.embedding_requests.append(body)
            inputs = body["input"] if isinstance(body["input"], list) else [body["input"]]
            dims = int(body.get("dimensions") or 1536)
            data = [{"object": "embedding", "index": i, "embedding": embed(str(t), dims)} for i, t in enumerate(inputs)]
            tokens = sum(len(str(t)) for t in inputs) // 4 + 1
            return {
                "object": "list",
                "data": data,
                "model": body.get("model", "mock"),
                "usage": {"prompt_tokens": tokens, "total_tokens": tokens},
            }

        @app.get("/v1/models")
        async def models():
            return {"object": "list", "data": [{"id": "mock", "object": "model", "owned_by": "mock"}]}

        return app

    # --- chạy server ---
    def serve_in_thread(self, port: int = 0) -> str:
        """Chạy server trong thread nền (cho test). Trả base_url dạng http://127.0.0.1:PORT/v1."""
        self.base_url = serve_in_thread(self.app, port) + "/v1"
        return self.base_url


def serve_in_thread(app: Any, port: int = 0) -> str:
    """Chạy một ứng dụng ASGI (mock này, hoặc AgentOS) bằng uvicorn trong thread nền. Trả http://127.0.0.1:PORT."""
    if port == 0:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    deadline = time.time() + 20
    while not server.started:
        if time.time() > deadline:
            raise RuntimeError("server không khởi động được")
        time.sleep(0.02)
    return f"http://127.0.0.1:{port}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8900)
    args = parser.parse_args()
    print(f"Mock OpenAI ở http://127.0.0.1:{args.port}/v1 (chế độ tự động). Ctrl+C để dừng.")
    uvicorn.run(MockLLM().app, host="127.0.0.1", port=args.port, log_level="warning")
