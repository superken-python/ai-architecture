import json

import pytest

from rvt_ai.engines import mt_llama
from rvt_ai.engines.mt_llama import LlamaCppMtEngine


class _FakeResponse:
    def __init__(self, deltas: list[str]):
        self.deltas = deltas

    def raise_for_status(self) -> None:
        pass

    async def aiter_lines(self):
        for d in self.deltas:
            yield "data: " + json.dumps({"choices": [{"delta": {"content": d}}]}, ensure_ascii=False)
        yield "data: [DONE]"


class _FakeStream:
    def __init__(self, response: _FakeResponse):
        self.response = response

    async def __aenter__(self) -> _FakeResponse:
        return self.response

    async def __aexit__(self, *exc) -> bool:
        return False


class _FakeAsyncClient:
    """Thay httpx.AsyncClient: ghi lại payload gửi llama.cpp và trả về các delta cho sẵn."""

    payloads: list[dict] = []
    deltas: list[str] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *exc) -> bool:
        return False

    def stream(self, method: str, url: str, json: dict, headers: dict | None = None) -> _FakeStream:
        _FakeAsyncClient.payloads.append(json)
        return _FakeStream(_FakeResponse(_FakeAsyncClient.deltas))


@pytest.mark.asyncio
async def test_llama_request_does_not_stop_at_dash_or_bold(monkeypatch):
    # "—" và "**" từng nằm trong stop: llama.cpp dừng sinh ở đó nên "Đợi đã — ê!" chỉ còn "Đợi đã" (docs 08 §3.5)
    monkeypatch.setattr(mt_llama.httpx, "AsyncClient", _FakeAsyncClient)
    _FakeAsyncClient.payloads = []
    _FakeAsyncClient.deltas = ["Đợi", " đã", " —", " ê!"]

    engine = LlamaCppMtEngine(api_url="http://mt:8080/v1")
    out = "".join([d async for d in engine.translate_stream("待てよ!", "ja", "vi")])

    stop = _FakeAsyncClient.payloads[-1]["stop"]
    assert "—" not in stop
    assert "**" not in stop
    assert "\n" in stop  # vẫn dừng ở xuống dòng để chặn ghi chú nhiều dòng
    assert out == "Đợi đã — ê!"


@pytest.mark.asyncio
async def test_api_key_is_sent_and_payload_is_hosted(monkeypatch):
    # Gọi API lưu trữ: gửi khoá, tên model, và payload đã đổi sang dạng API (docs 09 §5.6)
    seen = {}

    class _Client(_FakeAsyncClient):
        def stream(self, method, url, json, headers=None):
            seen.update(json=json, headers=headers, url=url)
            return _FakeStream(_FakeResponse(["data: [DONE]"]))

    monkeypatch.setattr("rvt_ai.engines.mt_llama.httpx.AsyncClient", _Client)
    engine = LlamaCppMtEngine(api_url="https://api.example/v1", api_key="k-test", model="m-test")
    [_ async for _ in engine.translate_stream("ありがとう", "ja", "vi")]
    assert seen["headers"] == {"Authorization": "Bearer k-test"}
    assert seen["json"]["model"] == "m-test" and len(seen["json"]["stop"]) <= 4
    assert "top_p" not in seen["json"]
