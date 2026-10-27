from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ProfileType = Literal["fake", "cpu-dev", "fast", "balanced", "quality", "listen", "api-mt"]


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
    # Glossary cho bộ dịch: tên file trong packs/glossary, cách nhau bởi dấu phẩy, ví dụ "default,naruto"
    GLOSSARIES: str = "default"
    # Khi thu âm tab: nhận dạng thêm vùng audio to mà VAD bỏ sót (docs 09 §4.1). Tắt bằng RVT_VAD_PROBE=false
    VAD_PROBE: bool = True
    # Đổi model nhận dạng theo ngôn ngữ mà không sửa profile, ví dụ "ja=large-v3" hoặc
    # "ja=kotoba-tech/kotoba-whisper-v2.0-faster,vi=phowhisper-large-ct2" (docs 10 §13.6)
    ASR_MODELS: str = ""
    # beam_size cho lượt nhận dạng chốt câu; chữ tạm luôn dùng 1 (docs 10 §10.4). 1 = như trước
    ASR_FINAL_BEAM_SIZE: int = 1

    # Security
    API_KEY: str = ""
    ACCESS_CODE: str = ""
    TOKEN_SECRET: str = "rvt-default-secret-change-in-production"
    TOKEN_TTL_MINUTES: int = 15

    # External services
    MT_API_URL: str = "http://localhost:8080/v1"
    MT_TIMEOUT_SEC: float = 5.0
    # Dịch qua API trên cloud (profile api-mt, docs 10 §13). MT_API_URL là URL gốc hoặc nguyên "Target URI" của
    # deployment Azure (…/openai/deployments/<tên>/chat/completions?api-version=…). Khoá chỉ đặt qua biến môi trường.
    MT_API_KEY: str = ""
    # azure | openai; để trống thì đoán theo URL
    MT_PROVIDER: str = ""
    # Tên model (OpenAI, Azure v1). URL deployment của Azure đã có tên deployment thì để trống
    MT_MODEL: str = ""
    # auto: mức suy luận thấp nhất theo tên model (gpt-5.4-mini: none, gpt-5-mini: minimal); "" để không gửi
    MT_REASONING_EFFORT: str = "auto"
    MT_MAX_COMPLETION_TOKENS: int = 1024

    # LAN / Deployment
    LAN_IP: str = "127.0.0.1"


settings = Settings()
