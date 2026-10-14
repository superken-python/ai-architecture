from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from excel_agent.core.config import settings
from excel_agent.core.logging import app_logger


class LLMResult(BaseModel):
    """Mô hình dữ liệu kết quả suy luận LLM."""

    content: str = Field(..., description="Văn bản phản hồi")
    model_name: str = Field(..., description="Tên mô hình đã dùng")
    is_mock: bool = Field(default=False, description="Có phải phản hồi giả lập hay không")


class LLMStrategy(ABC):
    """Giao diện Strategy cho việc tích hợp mô hình ngôn ngữ lớn."""

    @abstractmethod
    async def generate_response(self, prompt: str, system_prompt: str | None = None) -> LLMResult:
        """Sinh phản hồi từ mô hình."""


class AzureOpenAILLMStrategy(LLMStrategy):
    """
    Strategy triển khai mô hình Azure OpenAI (gpt-5-mini) thông qua Agno SDK hoặc OpenAI Client.
    """

    def __init__(self):
        self.api_key = settings.AZURE_OPENAI_API_KEY
        self.endpoint = settings.AZURE_OPENAI_ENDPOINT
        self.deployment = settings.AZURE_DEPLOYMENT_NAME
        self.api_version = settings.AZURE_OPENAI_API_VERSION
        self.model_name = settings.AZURE_OPENAI_MODEL

    async def generate_response(self, prompt: str, system_prompt: str | None = None) -> LLMResult:
        # Nếu chưa cấu hình API Key thực, tự động fallback sang Mock Strategy
        if not self.api_key or "your-azure" in self.api_key:
            app_logger.warning("Chưa cấu hình AZURE_OPENAI_API_KEY hợp lệ trong .env. Sử dụng Fallback Strategy.")
            fallback = MockLLMStrategy()
            return await fallback.generate_response(prompt, system_prompt)

        try:
            # Thử nạp Agno AzureOpenAI hoặc OpenAI client
            from openai import AsyncAzureOpenAI

            client = AsyncAzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version=self.api_version,
            )

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                temperature=0.3,
            )

            reply = response.choices[0].message.content or ""
            return LLMResult(content=reply, model_name=f"azure/{self.deployment}", is_mock=False)

        except Exception as e:  # noqa: BLE001
            app_logger.error(f"Lỗi khi gọi Azure OpenAI: {e!s}. Tự động fallback để giữ hệ thống hoạt động.")
            fallback = MockLLMStrategy()
            return await fallback.generate_response(prompt, system_prompt)


class MockLLMStrategy(LLMStrategy):
    """
    Mock Strategy cung cấp phản hồi thông minh ngay cả khi chưa có Azure OpenAI API key trong .env.
    Giúp lập trình viên kiểm thử toàn bộ luồng Excel Add-in ngay lập tức.
    """

    async def generate_response(self, prompt: str, system_prompt: str | None = None) -> LLMResult:
        query_lower = prompt.lower()
        if "tìm" in query_lower or "search" in query_lower:
            reply = (
                "Tôi đã kiểm tra cơ sở dữ liệu và bảng tính. "
                "Đã tìm thấy thông tin sản phẩm tương ứng trong danh mục doanh nghiệp. "
                "Bạn có thể xác nhận chèn dòng này vào Excel qua thẻ Preview bên dưới."
            )
        elif "chèn" in query_lower or "insert" in query_lower:
            reply = (
                "Tôi đã tạo đề xuất chèn dòng mới vào bảng tính Excel hiện tại. "
                "Vui lòng xem trước thông tin tại thẻ Preview và bấm 'Xác nhận (Apply)' để hoàn tất."
            )
        else:
            reply = (
                "Xin chào! Tôi là Trợ lý AI Bảng tính (AgentOS Agno). "
                "Tôi có thể giúp bạn tra cứu cơ sở dữ liệu doanh nghiệp (/search), "
                "tìm kiếm theo cột, và chèn nguyên một dòng dữ liệu vào Excel. "
                "Hãy gõ câu hỏi hoặc lệnh như `/search Áo thun`!"
            )

        return LLMResult(content=reply, model_name="mock-azure-gpt-5-mini", is_mock=True)
