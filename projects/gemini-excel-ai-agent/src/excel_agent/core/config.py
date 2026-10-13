from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Cấu hình hệ sinh thái Excel AI Agent sử dụng Agno SDK và Azure OpenAI.
    Tuân thủ quy chuẩn Zero-Hardcoding: toàn bộ thông số nạp qua biến môi trường (.env).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 1. Server & Environment
    HOST: str = Field(default="0.0.0.0", description="Host lắng nghe của server")
    PORT: int = Field(default=8000, description="Cổng dịch vụ")
    ENVIRONMENT: str = Field(default="development", description="Môi trường chạy: development / production")
    DEBUG: bool = Field(default=True, description="Chế độ debug")
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:8000",
            "https://localhost:8000",
            "https://localhost:3000",
            "https://appsforoffice.microsoft.com",
        ],
        description="Danh sách domain cho phép CORS",
    )

    # 2. Azure OpenAI Configuration (gpt-5-mini)
    AZURE_OPENAI_API_KEY: str = Field(
        default="",
        description="API Key của Azure OpenAI Service (cung cấp qua .env)",
    )
    AZURE_OPENAI_ENDPOINT: str = Field(
        default="https://your-resource.openai.azure.com/",
        description="Endpoint của Azure OpenAI Service",
    )
    AZURE_OPENAI_API_VERSION: str = Field(
        default="2024-08-01-preview",
        description="API version của Azure OpenAI",
    )
    AZURE_DEPLOYMENT_NAME: str = Field(
        default="gpt-5-mini",
        description="Deployment Name cho mô hình gpt-5-mini trên Azure",
    )
    AZURE_OPENAI_MODEL: str = Field(
        default="gpt-5-mini",
        description="Tên mô hình logic",
    )

    # 3. Agno AgentOS Settings
    AGENT_ID: str = Field(default="excel-copilot-agent", description="ID định danh Agent trong Agno")
    AGENT_NAME: str = Field(default="Excel Enterprise Copilot", description="Tên hiển thị Agent")
    AGENT_STORAGE_DB: str = Field(
        default="sqlite:///./excel_agent.db",
        description="Database lưu trữ phiên làm việc của Agno",
    )
    MAX_CHAT_HISTORY: int = Field(default=20, description="Số tin nhắn ngữ cảnh tối đa")

    # 4. Observability & Logging
    LOG_LEVEL: str = Field(default="INFO", description="Mức log của loguru")
    LANGFUSE_PUBLIC_KEY: str = Field(default="", description="Langfuse Public Key")
    LANGFUSE_SECRET_KEY: str = Field(default="", description="Langfuse Secret Key")
    LANGFUSE_HOST: str = Field(default="https://cloud.langfuse.com", description="Langfuse Host")
    LANGFUSE_ENABLED: bool = Field(default=False, description="Bật/tắt tracing với Langfuse")


# Khởi tạo singleton settings
settings = Settings()
