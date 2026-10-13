from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseEnvelope(BaseModel, Generic[T]):
    """Vỏ bọc chuẩn hóa cho mọi phản hồi API."""

    success: bool = Field(default=True, description="Trạng thái thực thi")
    message: str = Field(default="Thành công", description="Thông điệp phản hồi")
    data: T | None = Field(default=None, description="Dữ liệu payload")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Thời gian phản hồi")


class HealthCheckResponse(BaseModel):
    """Thông tin trạng thái hoạt động của hệ thống."""

    status: str = Field(default="healthy", description="Trạng thái hệ thống")
    agent_id: str = Field(..., description="ID Agent")
    azure_model: str = Field(..., description="Mô hình Azure OpenAI cấu hình")
    agno_sdk_version: str = Field(default="agno-agentos-v3", description="Phiên bản Agno runtime")
    environment: str = Field(..., description="Môi trường hoạt động")
