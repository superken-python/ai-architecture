"""Hạ tầng test: model giả lập chạy một lần cho cả phiên, mỗi test có database riêng.

Thư mục này được pytest đưa vào sys.path, nên `import agno_lab`, `import service`... chạy được như khi bạn
chạy lệnh ở gốc project thực hành.
"""

from __future__ import annotations

import os

import httpx
import pytest
from agno.utils.http import set_default_async_client

import setup_assets
from mock_llm import MockLLM

_MOCK = MockLLM()


@pytest.fixture(scope="session", autouse=True)
def _environment():
    os.environ["OPENAI_BASE_URL"] = _MOCK.serve_in_thread()
    os.environ["OPENAI_API_KEY"] = "mock"
    os.environ["MODEL_ID"] = "mock"
    os.environ["AGNO_TELEMETRY"] = "false"
    setup_assets.main()  # seed idempotent: data/ của project tham chiếu
    yield


@pytest.fixture
def llm() -> MockLLM:
    """Model giả lập, đã xoá kịch bản và request của test trước."""
    _MOCK.reset()
    return _MOCK


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Mỗi test một file SQLite riêng — không test nào thấy session của test khác."""
    monkeypatch.setenv("AGNO_DB", str(tmp_path / "agno.db"))
    monkeypatch.setenv("AGNO_VECTORS", str(tmp_path / "lancedb"))
    return tmp_path / "agno.db"


@pytest.fixture(autouse=True)
def fresh_http_client():
    """Agno dùng MỘT httpx.AsyncClient cho cả tiến trình (model, A2AClient, AgentOSClient...), và kết nối của client
    gắn với event loop đã mở nó. Mỗi asyncio.run()/TestClient trong test là một loop mới → mỗi test một client mới.
    Chương trình thật không cần việc này: chỉ có một event loop (một asyncio.run hoặc server uvicorn)."""
    set_default_async_client(httpx.AsyncClient(timeout=60, follow_redirects=True))
