from abc import ABC, abstractmethod

from excel_agent.core.logging import app_logger
from excel_agent.pipelines.context import PipelineContext


class PipelineStep(ABC):
    """Giao diện trừu tượng cho một bước trong Pipeline."""

    @abstractmethod
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """Thực thi logic của bước và trả về Context đã cập nhật."""


class ParseCommandStep(PipelineStep):
    """
    Bước 1: Phân tích cú pháp đầu vào để nhận diện Slash Command hoặc hội thoại tự nhiên.
    """

    async def execute(self, context: PipelineContext) -> PipelineContext:
        text = context.raw_input.strip()

        if text.startswith("/"):
            context.is_slash_command = True
            parts = text[1:].split(maxsplit=1)
            context.command_name = parts[0].lower()
            context.command_args = parts[1].strip() if len(parts) > 1 else ""
            app_logger.bind(
                command=context.command_name,
                args=context.command_args,
            ).info("Đã nhận diện Slash Command")
        else:
            context.is_slash_command = False
            # Nếu người dùng gõ tự nhiên chứa "tìm" hoặc "search"
            lower_text = text.lower()
            if any(k in lower_text for k in ["tìm", "search", "tra cứu", "lấy mã"]):
                context.command_name = "search"
                context.command_args = text
            elif any(k in lower_text for k in ["chèn", "thêm dòng", "insert", "add row"]):
                context.command_name = "insert"
                context.command_args = text

        return context
