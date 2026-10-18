"""Phần 16 — Eval: đo agent trước khi tin nó.

- ReliabilityEval: agent có gọi đúng tool, đúng tham số không. Không cần LLM giám khảo → rẻ, tất định.
- AccuracyEval: chạy agent, rồi một LLM giám khảo so câu trả lời với đáp án mẫu, chấm 1–10.
- AgentAsJudgeEval: LLM giám khảo chấm theo tiêu chí (đạt/không đạt hoặc 1–10), không cần đáp án mẫu.
- PerformanceEval: đo thời gian (và bộ nhớ) của một hàm, ví dụ dựng agent hay chạy một run.
- run_cases([Case...]): gom nhiều case thành một bộ, trả SuiteResult có status PASS/FAIL để chặn CI.

Có db thì mỗi lần eval được lưu lại → AgentOS hiển thị ở GET /eval-runs.
Giám khảo mặc định của Agno là model OpenAI (o4-mini, gpt-5-mini): dùng model local hay endpoint tương thích thì
LUÔN truyền model= cho giám khảo.

    uv run python -m agno_lab.p16_evals
"""

from __future__ import annotations

from agno.eval.accuracy import AccuracyEval, AccuracyResult
from agno.eval.agent_as_judge import AgentAsJudgeEval, AgentAsJudgeResult
from agno.eval.performance import PerformanceEval, PerformanceResult
from agno.eval.reliability import ReliabilityEval, ReliabilityResult
from agno.eval.suite import Case, SuiteResult, run_cases
from agno.run.agent import RunOutput

from agno_lab.p01_agent import build_agent
from agno_lab.settings import db, model

QUESTION = "Phòng ban nào bị cảnh báo ở 2026-Q2?"
EXPECTED = (
    "CLOUD_OPS cảnh báo vàng (KPI_02, chi phí tăng 18%) và FIN_TECH cần giải trình (KPI_03, doanh thu giảm 12,5%)."
)
NO_OUTSIDE_DATA = "Câu trả lời chỉ dùng số liệu nội bộ, không nhắc nguồn web, benchmark hay số liệu thị trường."


def reliability(run: RunOutput) -> ReliabilityResult:
    """Chấm một run CÓ SẴN: đúng tool, đúng tham số."""
    return ReliabilityEval(
        name="kpi-dung-tool",
        agent_response=run,
        expected_tool_calls=["get_quarter_kpis"],
        expected_tool_call_arguments={"get_quarter_kpis": {"quarter": "2026-Q2"}},
        db=db(),
    ).run()


def accuracy() -> AccuracyResult:
    """Tự chạy agent với input, rồi giám khảo so với đáp án mẫu."""
    return AccuracyEval(
        name="canh-bao-2026-Q2",
        agent=build_agent(),
        input=QUESTION,
        expected_output=EXPECTED,
        model=model(),  # giám khảo
        additional_guidelines=[
            "Thiếu một phòng ban bị cảnh báo thì tối đa 5 điểm.",
            "Không trừ điểm vì cách diễn đạt.",
        ],
        num_iterations=1,  # >1 để thấy độ dao động (trung bình, độ lệch chuẩn)
        db=db(),
    ).run(print_summary=False, print_results=False)


def judge(output: str) -> AgentAsJudgeResult:
    """Chấm một câu trả lời theo tiêu chí — dùng được cho output lấy từ log production."""
    return AgentAsJudgeEval(
        name="khong-dung-nguon-ngoai",
        criteria=NO_OUTSIDE_DATA,
        scoring_strategy="binary",
        model=model(),
        db=db(),
    ).run(input=QUESTION, output=output)


def performance() -> PerformanceResult:
    """Dựng agent tốn bao lâu (không gọi model) — chạy nhiều lần, bỏ vài lần khởi động."""
    return PerformanceEval(name="dung-agent", func=build_agent, num_iterations=20, warmup_runs=2, db=db()).run()


def cases() -> list[Case]:
    agent = build_agent()
    return [
        Case(
            name="canh-bao-q2",
            input=QUESTION,
            agent=agent,
            tags=("smoke",),
            criteria=NO_OUTSIDE_DATA,
            expected_tool_calls=("get_quarter_kpis",),
        ),
        Case(
            name="ly-do-kpi02",
            input="Vì sao CLOUD_OPS bị cảnh báo ở 2026-Q2?",
            agent=agent,
            expected_tool_calls=("get_quarter_kpis", "inspect_rules"),
        ),
    ]


def suite(tag: str | None = None) -> SuiteResult:
    return run_cases(cases(), tag=tag, judge_model=model(), db=db())


if __name__ == "__main__":
    result = suite()
    for case in result.to_dict()["cases"]:
        checks = f"judge={case['judge_passed']} reliability={case['reliability_passed']}"
        print(f"{case['name']:<14} passed={case['passed']} {checks} tools={case['tools_called']}")
    print("SUITE:", result.status)
