"""Phần 2 — Input/Output có cấu trúc: input_schema, output_schema, và việc của LLM tách khỏi việc của code.

uv run python -m agno_lab.p02_structured 2026-Q2 "Lập báo cáo, nêu hai rủi ro chính"
"""

from __future__ import annotations

import sys

from agno.agent import Agent
from pydantic import BaseModel, Field

from agno_lab.p01_agent import KpiTools, inspect_rules, previous_quarter
from agno_lab.settings import model
from reporting import Narrative, make_evidence, render_report
from service import read_metrics


class ReportRequest(BaseModel):
    """Input có kiểu: sai định dạng thì lỗi TRƯỚC khi tốn một lượt gọi model."""

    quarter: str = Field(pattern=r"^\d{4}-Q[1-4]$", description="Quý cần báo cáo, ví dụ 2026-Q2")
    instruction: str = Field(min_length=3, max_length=500, description="Yêu cầu của người dùng")


class NarrativeInvalid(RuntimeError):
    """Model trả output không đúng schema. Agno chỉ log WARNING và để content là chuỗi — ta phải tự chặn."""


def build_writer(json_mode: bool = False) -> Agent:
    return Agent(
        id="report-writer",
        name="Report Writer",
        model=model(),
        input_schema=ReportRequest,
        output_schema=Narrative,  # model trả JSON theo schema; run.content là Narrative
        use_json_mode=json_mode,  # True cho model không hỗ trợ json_schema (một số model local)
        tools=[KpiTools(), inspect_rules],
        instructions=[
            "Viết narrative cho báo cáo KPI bằng tiếng Việt.",
            "Gọi get_quarter_kpis cho đúng quý trong input trước khi viết.",
            "Chỉ dùng số từ kết quả tool. Không viết bảng số liệu — ứng dụng tự render bảng.",
        ],
    )


def write_narrative(request: ReportRequest, agent: Agent | None = None) -> Narrative:
    run = (agent or build_writer()).run(input=request)
    if not isinstance(run.content, Narrative):
        raise NarrativeInvalid(f"Output không đúng schema Narrative: {str(run.content)[:200]}")
    return run.content


def build_report(request: ReportRequest, revision: int = 1) -> str:
    """LLM viết nhận xét; code tính số và render bảng. Số liệu không bao giờ đi qua LLM."""
    narrative = write_narrative(request)
    evidence = make_evidence(read_metrics(request.quarter), read_metrics(previous_quarter(request.quarter)))
    return render_report(evidence, narrative, revision)


if __name__ == "__main__":
    quarter, instruction = (sys.argv[1], sys.argv[2]) if len(sys.argv) == 3 else ("2026-Q2", "Lập báo cáo KPI")
    print(build_report(ReportRequest(quarter=quarter, instruction=instruction)))
