"""Phần 8 — Guardrail, pre/post hook, retry và model dự phòng: chặn bằng code trước và sau model.

uv run python -m agno_lab.p08_guardrails "Báo cáo KPI 2026-Q2, gửi về lan@corp.vn"
"""

from __future__ import annotations

import re
import sys

from agno.agent import Agent, RunOutput
from agno.exceptions import CheckTrigger, InputCheckError, OutputCheckError
from agno.guardrails import PIIDetectionGuardrail, PromptInjectionGuardrail
from agno.models.fallback import FallbackConfig
from agno.models.openai import OpenAIChat
from agno.run.agent import RunInput

from agno_lab.p01_agent import KpiTools
from agno_lab.settings import model

FALLBACKS: list[str] = []  # ghi lại mỗi lần phải dùng model dự phòng


def require_quarter(run_input: RunInput) -> None:
    """Pre-hook tự viết: tham số được Agno truyền THEO TÊN (run_input, agent, session, run_context...)."""
    if not re.search(r"\d{4}-Q[1-4]", run_input.input_content_string()):
        raise InputCheckError("Yêu cầu phải nêu quý dạng 2026-Q2", check_trigger=CheckTrigger.VALIDATION_FAILED)


def no_external_sources(run_output: RunOutput) -> None:
    """Post-hook: Lab 00 cấm nguồn web bịa trong báo cáo dùng fixture."""
    if re.search(r"https?://", str(run_output.content)):
        raise OutputCheckError(
            "Câu trả lời chứa URL — không được dẫn nguồn web", check_trigger=CheckTrigger.OUTPUT_NOT_ALLOWED
        )


def on_fallback(primary: str, fallback: str, error: Exception) -> None:
    FALLBACKS.append(f"{primary} -> {fallback}: {type(error).__name__}")


def build_agent(primary: OpenAIChat | None = None) -> Agent:
    return Agent(
        id="guarded-analyst",
        name="Guarded Analyst",
        model=primary or model(),
        fallback_config=FallbackConfig(on_error=[model()], callback=on_fallback),  # model chính lỗi → model này
        tools=[KpiTools()],
        pre_hooks=[  # chạy theo thứ tự, TRƯỚC khi gọi model
            PromptInjectionGuardrail(),  # chặn "ignore previous instructions..." (theo mẫu câu)
            PIIDetectionGuardrail(mask_pii=True),  # che email/điện thoại/thẻ thay vì chặn
            require_quarter,
        ],
        post_hooks=[no_external_sources],  # chạy SAU khi có câu trả lời
        instructions=["Phân tích KPI bằng tiếng Việt, chỉ dùng số liệu từ get_quarter_kpis."],
    )


def safe_answer(run: RunOutput) -> str:
    """Bị guardrail chặn thì status=ERROR — và content có thể vẫn là câu trả lời vi phạm. Luôn kiểm status trước."""
    if run.status.value != "COMPLETED":
        return f"[bị chặn] {run.content if run.content and 'http' not in str(run.content) else 'vi phạm chính sách'}"
    return str(run.content)


if __name__ == "__main__":
    print(safe_answer(build_agent().run(sys.argv[1] if len(sys.argv) > 1 else "Báo cáo KPI 2026-Q2")))
