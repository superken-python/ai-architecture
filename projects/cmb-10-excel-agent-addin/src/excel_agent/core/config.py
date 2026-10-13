"""Cấu hình tập trung — mọi giá trị đọc từ biến môi trường hoặc file `.env` (không hard-code)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Excel Agent POC"
    host: str = "127.0.0.1"
    port: int = 7777

    # --- Agent (OpenAI Agents SDK) ---
    openai_api_key: SecretStr | None = Field(default=None, description="Để trống → chạy chế độ offline")
    openai_model: str = "gpt-5-mini"
    openai_base_url: str | None = None  # gateway tương thích OpenAI (để trống → api.openai.com)
    openai_reasoning_effort: Literal["minimal", "low", "medium", "high"] = "low"
    # auto: có OPENAI_API_KEY thì dùng OpenAI, không có thì dùng model offline (luật cố định)
    agent_mode: Literal["auto", "openai", "offline"] = "auto"
    use_triage: bool = True  # agent điều phối + handoff sang agent chuyên trách
    max_turns: int = 8
    # Mặc định KHÔNG gửi trace của OpenAI Agents SDK lên nền tảng OpenAI
    openai_tracing: bool = False

    # --- API dữ liệu (giả lập ERP/CRM) ---
    data_api_url: str | None = None  # để trống → dùng API giả lập gắn trong cùng server
    mount_mock_api: bool = True
    default_dataset: str = "khach_hang"

    # --- Lưu trữ ---
    storage_dir: Path = PROJECT_ROOT / "var"
    max_preview_rows: int = 500
    max_tool_rows: int = 20
    max_apply_rows: int = 200

    cors_origins: list[str] = ["http://localhost:7777", "http://127.0.0.1:7777"]

    @property
    def resolved_data_api_url(self) -> str:
        return self.data_api_url or f"http://{self.host}:{self.port}/mock-api"

    @property
    def resolved_mode(self) -> Literal["openai", "offline"]:
        if self.agent_mode == "auto":
            return "openai" if self.openai_api_key else "offline"
        return self.agent_mode

    @property
    def workbooks_dir(self) -> Path:
        return self.storage_dir / "workbooks"

    @property
    def db_file(self) -> Path:
        return self.storage_dir / "agentos.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
