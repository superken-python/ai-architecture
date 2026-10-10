from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ProfileType = Literal["fake", "cpu-dev", "fast", "balanced", "quality"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RVT_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Core service settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    PROFILE: ProfileType = "fake"
    USE_FAKE: bool = True
    MAX_SESSIONS: int = 4
    SESSION_IDLE_TIMEOUT_SEC: int = 300
    SESSION_MAX_DURATION_SEC: int = 7200

    # Paths
    MODELS_DIR: str = "models"
    CONFIG_DIR: str = "config"
    PACKS_DIR: str = "packs"
    PROMPTS_DIR: str = "prompts"

    # Security
    API_KEY: str = ""
    ACCESS_CODE: str = ""
    TOKEN_SECRET: str = "rvt-default-secret-change-in-production"
    TOKEN_TTL_MINUTES: int = 15

    # External services
    MT_API_URL: str = "http://localhost:8080/v1"
    MT_TIMEOUT_SEC: float = 5.0

    # LAN / Deployment
    LAN_IP: str = "127.0.0.1"


settings = Settings()
