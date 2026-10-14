from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from excel_agent.core.logging import app_logger


class AssembledPrompt(BaseModel):
    """Mô hình dữ liệu chứa prompt đã lắp ráp hoàn chỉnh."""

    system_prompt: str = Field(..., description="Prompt chỉ dẫn hệ thống")
    context: str = Field(..., description="Ngữ cảnh dữ liệu được tiêm vào")
    critical_rules: str = Field(..., description="Các quy tắc an toàn bắt buộc")
    user_prompt: str = Field(..., description="Prompt câu hỏi người dùng")
    full_instruction: str = Field(..., description="Toàn bộ chỉ dẫn tổng hợp")


class PromptBuilder:
    """
    Builder nạp prompt từ file .yml trong thư mục prompts/,
    tiêm các biến động và lắp ráp theo cấu trúc chuẩn trước khi gửi cho Agent.
    """

    def __init__(self, base_prompts_dir: Path | None = None):
        if base_prompts_dir is None:
            # projects/gemini-excel-ai-agent/prompts/
            self.prompts_dir = Path(__file__).resolve().parent.parent.parent.parent / "prompts"
        else:
            self.prompts_dir = base_prompts_dir

    def load_and_assemble(self, prompt_file: str, variables: dict[str, Any]) -> AssembledPrompt:
        """
        Nạp file YAML và tiêm biến vào các trường.
        """
        file_path = self.prompts_dir / prompt_file
        if not file_path.exists():
            app_logger.warning(f"File prompt không tồn tại: {file_path}, dùng fallback prompt mặc định")
            return self._fallback_prompt(variables)

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        raw_system = data.get("system_prompt", "")
        raw_context = data.get("context", "")
        raw_critical_rules = data.get("critical_rules", "")
        raw_user = data.get("user_prompt", "")

        # Tiêm biến bằng safe format
        system_formatted = self._format_safe(raw_system, variables)
        context_formatted = self._format_safe(raw_context, variables)
        rules_formatted = self._format_safe(raw_critical_rules, variables)
        user_formatted = self._format_safe(raw_user, variables)

        full_instruction = (
            f"{system_formatted}\n\n"
            f"--- BỐI CẢNH ---\n{context_formatted}\n\n"
            f"--- QUY TẮC BẮT BUỘC ---\n{rules_formatted}"
        )

        return AssembledPrompt(
            system_prompt=system_formatted,
            context=context_formatted,
            critical_rules=rules_formatted,
            user_prompt=user_formatted,
            full_instruction=full_instruction,
        )

    @staticmethod
    def _format_safe(template_str: str, variables: dict[str, Any]) -> str:
        res = template_str
        for k, v in variables.items():
            res = res.replace(f"{{{k}}}", str(v))
        return res

    @staticmethod
    def _fallback_prompt(variables: dict[str, Any]) -> AssembledPrompt:
        return AssembledPrompt(
            system_prompt="Bạn là trợ lý Excel AI chuyên nghiệp.",
            context=f"Bối cảnh: {variables}",
            critical_rules="Luôn kiểm tra dữ liệu trước khi chèn.",
            user_prompt=str(variables.get("user_query", "")),
            full_instruction="Bạn là trợ lý Excel AI chuyên nghiệp.",
        )
