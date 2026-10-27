"""Dịch qua API trên cloud: Azure OpenAI, OpenAI (docs 10 §13)."""

import json

import httpx
import pytest

from rvt_ai.engines import mt_llama
from rvt_ai.engines.mt_llama import LlamaCppMtEngine, default_reasoning_effort, deployment_from_url

# Dạng "Target URI" của một deployment Azure (tên resource là ví dụ)
AZURE_TARGET_URI = (
    "https://example.cognitiveservices.azure.com/openai/deployments/gpt-5.4-mini/chat/completions"
    "?api-version=2024-12-01-preview"
)
PAYLOAD = {"messages": [{"role": "user", "content": "x"}], "stream": True, "max_tokens": 64, "temperature": 0.1,
           "top_p": 0.7, "stop": ["\n"]}  # fmt: skip


def test_azure_target_uri_is_used_as_is():
    engine = LlamaCppMtEngine(api_url=AZURE_TARGET_URI, api_key="k", reasoning_effort="auto")
    url, headers, body = engine.request(PAYLOAD)
    assert engine.provider == "azure" and engine.deployment == "gpt-5.4-mini"
    assert url == AZURE_TARGET_URI
    assert headers == {"api-key": "k"}
    assert "model" not in body  # tên deployment đã nằm trong URL
    assert body["reasoning_effort"] == "none"  # gpt-5.4-mini: thấp nhất và cũng là mặc định
    assert "max_completion_tokens" not in body  # tránh làm "none" bị bỏ qua
    assert not {"stop", "temperature", "top_p", "max_tokens"} & set(body)


def test_azure_v1_and_openai_base_urls():
    azure = LlamaCppMtEngine(
        api_url="https://res.openai.azure.com/openai/v1/", api_key="k", model="gpt-5-mini", reasoning_effort="auto"
    )
    url, headers, body = azure.request(PAYLOAD)
    assert url == "https://res.openai.azure.com/openai/v1/chat/completions" and headers == {"api-key": "k"}
    assert body["model"] == "gpt-5-mini" and body["reasoning_effort"] == "minimal"
    assert body["max_completion_tokens"] == 1024

    openai = LlamaCppMtEngine(api_url="https://api.openai.com/v1", api_key="k", model="gpt-5-mini")
    url, headers, _ = openai.request(PAYLOAD)
    assert openai.provider == "openai" and headers == {"Authorization": "Bearer k"}
    assert url == "https://api.openai.com/v1/chat/completions"


def test_local_llama_cpp_request_is_unchanged():
    engine = LlamaCppMtEngine(api_url="http://mt:8080/v1")
    url, headers, body = engine.request(PAYLOAD)
    assert engine.provider == "llama-cpp" and url == "http://mt:8080/v1/chat/completions"
    assert headers == {} and body is PAYLOAD


@pytest.mark.parametrize(
    ("model", "effort"),
    [("gpt-5.4-mini", "none"), ("gpt-5.1", "none"), ("gpt-5-mini", "minimal"), ("gpt-5", "minimal"),
     ("gpt-4o-mini", ""), ("my-deployment", "")],
)  # fmt: skip
def test_default_reasoning_effort(model, effort):
    assert default_reasoning_effort(model) == effort


def test_deployment_from_url():
    assert deployment_from_url(AZURE_TARGET_URI) == "gpt-5.4-mini"
    assert deployment_from_url("https://api.openai.com/v1") == ""


def _error(message: str, param: str | None = None) -> str:
    return json.dumps({"error": {"message": message, "type": "invalid_request_error", "param": param}})


def test_rejected_minimal_switches_to_listed_none():
    engine = LlamaCppMtEngine(api_url=AZURE_TARGET_URI, api_key="k", reasoning_effort="minimal")
    msg = (
        "Unsupported value: 'reasoning_effort' does not support 'minimal' with this model. "
        "Supported values are: 'none', 'low', 'medium', 'high', and 'xhigh'."
    )
    assert engine.adapt_to_error(_error(msg, "reasoning_effort"), {"reasoning_effort": "minimal"})
    assert engine.reasoning_effort == "none"
    assert "max_completion_tokens" not in engine.request(PAYLOAD)[2]


def test_rejected_none_drops_reasoning_effort():
    # api-version cũ chỉ nhận low/medium/high: bỏ hẳn tham số thay vì bắt model suy luận "low"
    engine = LlamaCppMtEngine(api_url=AZURE_TARGET_URI, api_key="k", reasoning_effort="auto")
    msg = "Invalid value: 'none'. Supported values are: 'low', 'medium', and 'high'."
    assert engine.adapt_to_error(_error(msg, "reasoning_effort"), {"reasoning_effort": "none"})
    assert "reasoning_effort" not in engine.request(PAYLOAD)[2]


def test_rejected_parameter_is_dropped_but_other_errors_are_not_retried():
    engine = LlamaCppMtEngine(api_url="https://api.openai.com/v1", api_key="k", model="m", max_completion_tokens=512)
    sent = engine.request(PAYLOAD)[2]
    msg = "Unsupported parameter: 'max_completion_tokens' is not supported with this model."
    assert engine.adapt_to_error(_error(msg, "max_completion_tokens"), sent)
    assert "max_completion_tokens" not in engine.request(PAYLOAD)[2]
    filtered = "The response was filtered due to the prompt triggering Azure OpenAI's content management policy."
    assert not engine.adapt_to_error(_error(filtered, "prompt"), sent)
    assert not engine.adapt_to_error("<html>Bad Request</html>", sent)


class _Response:
    def __init__(self, status: int, lines: list[str] | None = None, body: str = ""):
        self.status_code = status
        self.lines = lines or []
        self.body = body.encode()

    async def aread(self) -> bytes:
        return self.body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://example")
            raise httpx.HTTPStatusError("error", request=request, response=httpx.Response(self.status_code))

    async def aiter_lines(self):
        for line in self.lines:
            yield line


class _Stream:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, *exc):
        return False


class _Client:
    calls: list = []
    responses: list = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def stream(self, method, url, json, headers=None):
        _Client.calls.append({"url": url, "headers": headers, "body": json})
        return _Stream(_Client.responses.pop(0))


def _sse(*contents: str) -> list[str]:
    # Azure gửi trước một chunk không có choices (kết quả lọc nội dung của prompt)
    chunks = [{"choices": [], "prompt_filter_results": []}]
    chunks += [{"choices": [{"delta": {"content": c}}]} for c in contents]
    return [f"data: {json.dumps(c, ensure_ascii=False)}" for c in chunks] + ["data: [DONE]"]


@pytest.mark.asyncio
async def test_stream_retries_after_rejected_parameter_and_keeps_first_line(monkeypatch):
    monkeypatch.setattr(mt_llama.httpx, "AsyncClient", _Client)
    msg = "Unsupported value: 'reasoning_effort' does not support 'minimal' with this model. Supported values: 'none'."
    _Client.calls = []
    _Client.responses = [
        _Response(400, body=_error(msg, "reasoning_effort")),
        _Response(200, _sse("Cảm ơn", " mọi người.", "\nNote: lời cảm ơn lịch sự")),
    ]
    engine = LlamaCppMtEngine(api_url=AZURE_TARGET_URI, api_key="k", reasoning_effort="minimal")
    out = "".join([d async for d in engine.translate_stream("ありがとうございました。", "ja", "vi")])
    assert out == "Cảm ơn mọi người."
    assert [c["body"].get("reasoning_effort") for c in _Client.calls] == ["minimal", "none"]
    assert all(c["headers"] == {"api-key": "k"} for c in _Client.calls)


@pytest.mark.asyncio
async def test_stream_raises_on_auth_error(monkeypatch):
    monkeypatch.setattr(mt_llama.httpx, "AsyncClient", _Client)
    _Client.calls = []
    _Client.responses = [_Response(401, body=_error("Access denied due to invalid subscription key."))]
    engine = LlamaCppMtEngine(api_url=AZURE_TARGET_URI, api_key="wrong")
    with pytest.raises(httpx.HTTPStatusError):
        [_ async for _ in engine.translate_stream("はい。", "ja", "vi")]
    assert len(_Client.calls) == 1  # lỗi khoá không gửi lại


def test_api_profile_builds_hosted_engine_from_settings(monkeypatch):
    import os

    from rvt_ai.core.config import settings
    from rvt_ai.engines.registry import build_mt_engine
    from rvt_ai.packs.loader import PackRegistry

    packs = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../packs"))
    profile = PackRegistry(packs).get_profile("api-mt")
    monkeypatch.setattr(settings, "USE_FAKE", False)
    monkeypatch.setattr(settings, "MT_API_URL", AZURE_TARGET_URI)
    monkeypatch.setattr(settings, "MT_API_KEY", "k")
    mt = build_mt_engine(profile)
    assert isinstance(mt, LlamaCppMtEngine)
    assert mt.provider == "azure" and mt.model == "gpt-5.4-mini" and mt.reasoning_effort == "none"
    # URL gốc: tên model lấy từ RVT_MT_MODEL, không có thì theo profile
    monkeypatch.setattr(settings, "MT_API_URL", "https://res.openai.azure.com/openai/v1")
    assert build_mt_engine(profile).model == "gpt-5.4-mini"
    monkeypatch.setattr(settings, "MT_MODEL", "gpt-5-mini")
    assert build_mt_engine(profile).reasoning_effort == "minimal"
