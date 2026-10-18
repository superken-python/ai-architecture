"""Phần 1 — Agent đầu tiên: model, instructions, tool (hàm và Toolkit), chạy và đọc RunOutput.

uv run python -m agno_lab.p01_agent "Phòng ban nào bị cảnh báo ở 2026-Q2?"
"""

from __future__ import annotations

import json
import sys

from agno.agent import Agent, RunOutput
from agno.tools import Toolkit

from agno_lab.settings import model
from reporting import make_evidence
from rules import load_rules
from service import read_metrics


def previous_quarter(quarter: str) -> str:
    year, number = int(quarter[:4]), int(quarter[-1])
    return f"{year - 1}-Q4" if number == 1 else f"{year}-Q{number - 1}"


# Tool dạng hàm: Agno đọc tên hàm, type hint và docstring để tạo JSON schema gửi cho model.
# Docstring là "hướng dẫn sử dụng" model đọc — viết rõ khi nào dùng.
def inspect_rules() -> str:
    """Đọc toàn bộ quy ước KPI từ Excel: rule_id, phòng ban, loại rule, ngưỡng và nhãn cảnh báo.

    Dùng khi cần biết vì sao một phòng ban bị cảnh báo hoặc ngưỡng của rule là bao nhiêu.
    """
    return json.dumps(load_rules(), ensure_ascii=False)


# Tool dạng Toolkit: gom nhiều hàm liên quan, chia sẻ cấu hình (cache, include/exclude, instructions...).
class KpiTools(Toolkit):
    def __init__(self, **options) -> None:  # options của Toolkit: cache_results, include_tools, timeout...
        super().__init__(name="kpi_tools", tools=[self.get_quarter_kpis], **options)

    def get_quarter_kpis(self, quarter: str) -> str:
        """Tính KPI và cảnh báo của mọi phòng ban trong một quý (dạng YYYY-Q1..Q4), so với quý liền trước.

        Dùng khi người dùng hỏi số liệu, margin, tăng trưởng hoặc cảnh báo của một quý.
        """
        try:
            evidence = make_evidence(read_metrics(quarter), read_metrics(previous_quarter(quarter)))
        except ValueError as exc:  # lỗi có hướng dẫn → model tự sửa ở lượt sau, không làm hỏng run
            return f"Lỗi: {exc}. Quý phải có dạng 2026-Q2 và đã có dữ liệu."
        return json.dumps(evidence["kpis"], ensure_ascii=False)


def build_agent() -> Agent:
    return Agent(
        id="kpi-analyst",
        name="KPI Analyst",
        model=model(),
        description="Trợ lý phân tích KPI phòng ban từ database nội bộ.",
        instructions=[
            "Trả lời bằng tiếng Việt, ngắn gọn.",
            "Luôn lấy số liệu bằng get_quarter_kpis; không tự tính hay đoán số.",
            "Giải thích cảnh báo bằng rule_id và ngưỡng trong inspect_rules khi được hỏi lý do.",
        ],
        tools=[inspect_rules, KpiTools()],
        markdown=True,
    )


def describe(run: RunOutput) -> str:
    """Những gì nên nhìn sau mỗi run: nội dung, tool đã chạy, token."""
    lines = [f"status={run.status.value} run_id={run.run_id}", f"content: {run.content}"]
    for t in run.tools or []:
        lines.append(f"tool {t.tool_name}({t.tool_args}) -> {str(t.result)[:80]}")
    m = run.metrics
    lines.append(f"tokens: input={m.input_tokens} output={m.output_tokens} total={m.total_tokens}")
    return "\n".join(lines)


if __name__ == "__main__":
    question = sys.argv[1] if len(sys.argv) > 1 else "Phòng ban nào bị cảnh báo ở 2026-Q2?"
    print(describe(build_agent().run(question)))
