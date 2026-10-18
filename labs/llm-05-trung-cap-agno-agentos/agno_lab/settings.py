"""Cấu hình chung cho các phần của Lab 01: đọc .env, tạo model và database.

Mọi phần đều gọi `model()` và `db()` ở đây, nên đổi model (OpenAI, Ollama, vLLM, mock_llm) chỉ cần sửa .env.
"""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path

from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIChat
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def model(**kwargs) -> OpenAIChat:
    """Model dùng chung.

    MODEL_ID: tên model, không có prefix provider (gpt-5-mini, qwen3:8b, ...).
    OPENAI_BASE_URL (tuỳ chọn): endpoint tương thích OpenAI — mock_llm, Ollama, vLLM, LM Studio.
    """
    return OpenAIChat(id=os.environ["MODEL_ID"], base_url=os.getenv("OPENAI_BASE_URL") or None, **kwargs)


def db() -> SqliteDb:
    """Một file SQLite cho mọi phần (session, memory, eval, trace...). AGNO_DB đổi đường dẫn — test dùng thư mục tạm.

    Trả CÙNG một object cho cùng một file: AgentOS gom db của mọi agent/team/workflow theo id, hai object khác
    nhau trỏ cùng file sẽ bị cảnh báo "multiple distinct databases share id".
    """
    return _db(os.getenv("AGNO_DB", str(ROOT / "storage" / "agno_lab.db")))


@cache
def _db(path: str) -> SqliteDb:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return SqliteDb(db_file=path)


def vector_dir() -> Path:
    """Thư mục LanceDB cho Phần 6 (knowledge). AGNO_VECTORS đổi đường dẫn."""
    path = Path(os.getenv("AGNO_VECTORS", str(ROOT / "storage" / "lancedb")))
    path.mkdir(parents=True, exist_ok=True)
    return path
