"""Phần 11 — Workflow: luồng do CODE định nghĩa; agent chỉ làm bước cần ngôn ngữ.

gather (Parallel: quý này ‖ quý trước) → evidence → Router(mode)
    ├─ numbers_only: narrative cố định, không gọi LLM
    └─ full: Loop[prompt → write (agent) → gate] ≤ 3 lần → ensure_passed → Condition(có cảnh báo → escalate)
→ publish (HumanReview: người duyệt trước khi lưu)

uv run python -m agno_lab.p11_workflow report-01 2026-Q2 "Lập báo cáo, nêu rủi ro"
"""

from __future__ import annotations

import sys

from agno.agent import Agent
from agno.run import RunContext
from agno.workflow import Condition, HumanReview, Loop, Parallel, Router, Step, StepInput, StepOutput, Steps, Workflow

from agno_lab.p01_agent import previous_quarter
from agno_lab.p02_structured import ReportRequest
from agno_lab.settings import db, model
from reporting import Narrative, make_evidence, make_prompt, render_report, save_local_report
from service import read_metrics

WRITER = "Bạn viết narrative cho báo cáo KPI."
MAX_DRAFTS = 3


def request_of(step_input: StepInput) -> ReportRequest:
    value = step_input.input
    return value if isinstance(value, ReportRequest) else ReportRequest.model_validate(value)


# ---------------------------------------------------------------- bước hàm thuần (không LLM)
def fetch_current(step_input: StepInput) -> StepOutput:
    return StepOutput(content=read_metrics(request_of(step_input).quarter))


def fetch_previous(step_input: StepInput) -> StepOutput:
    return StepOutput(content=read_metrics(previous_quarter(request_of(step_input).quarter)))


def build_evidence(step_input: StepInput, run_context: RunContext) -> StepOutput:
    """run_context.session_state dùng chung cho mọi bước và được lưu theo session_id sau khi chạy."""
    evidence = make_evidence(step_input.get_step_content("current"), step_input.get_step_content("previous"))
    state = run_context.session_state
    state.update(evidence=evidence, attempt=0, feedback="", narrative=None, extra_actions=[])
    alerts = [row["dept_code"] for row in evidence["kpis"] if row["alert"] != "ĐẠT"]
    return StepOutput(content={"departments": len(evidence["kpis"]), "alerts": alerts})


def make_writer_prompt(step_input: StepInput, run_context: RunContext) -> StepOutput:
    state = run_context.session_state
    instruction = request_of(step_input).instruction
    if state["feedback"]:
        instruction += f"\nSửa theo nhận xét của lần trước: {state['feedback']}"
    return StepOutput(content=make_prompt(state["evidence"], instruction, state.get("report", "")))


def check_narrative(narrative: object, evidence: dict) -> list[str]:
    """Cổng kiểm tra bằng code: đúng schema, và tóm tắt phải nhắc mọi phòng ban bị cảnh báo."""
    if not isinstance(narrative, Narrative):
        return ["Output không đúng schema Narrative"]
    summary = " ".join(narrative.executive_summary)
    return [
        f"Tóm tắt chưa nhắc {row['dept_code']} ({row['alert']})"
        for row in evidence["kpis"]
        if row["alert"] != "ĐẠT" and row["dept_code"] not in summary and row["dept_name"] not in summary
    ]


def gate(step_input: StepInput, run_context: RunContext) -> StepOutput:
    state = run_context.session_state
    state["attempt"] += 1
    problems = check_narrative(step_input.previous_step_content, state["evidence"])
    state["feedback"] = "; ".join(problems)
    if not problems:
        state["narrative"] = step_input.previous_step_content.model_dump()
    return StepOutput(content={"ok": not problems, "attempt": state["attempt"], "problems": problems})


def gate_passed(outputs: list[StepOutput]) -> bool:
    """end_condition của Loop: nhận output các bước trong lượt vừa chạy."""
    return bool(outputs) and isinstance(outputs[-1].content, dict) and outputs[-1].content["ok"]


def ensure_passed(step_input: StepInput, run_context: RunContext) -> StepOutput:
    """Hết số lần viết mà vẫn sai thì DỪNG workflow, không lặng lẽ đi tiếp (lỗi đã chỉ ra ở Lab 00 §1)."""
    if run_context.session_state.get("narrative") is None:
        return StepOutput(content=f"Narrative không qua cổng sau {MAX_DRAFTS} lần", success=False, stop=True)
    return StepOutput(content="Narrative đạt")


def has_alerts(step_input: StepInput) -> bool:
    return bool(step_input.get_step_content("evidence")["alerts"])


def escalate(step_input: StepInput, run_context: RunContext) -> StepOutput:
    alerts = step_input.get_step_content("evidence")["alerts"]
    action = f"Họp xử lý cảnh báo với {', '.join(alerts)} trong tuần này"
    run_context.session_state["extra_actions"].append(action)
    return StepOutput(content=action)


def numbers_only(step_input: StepInput, run_context: RunContext) -> StepOutput:
    narrative = Narrative(executive_summary=["Báo cáo chỉ gồm số liệu."], actions=["Đọc bảng KPI."])
    run_context.session_state["narrative"] = narrative.model_dump()
    return StepOutput(content="Bỏ qua bước viết")


def publish(step_input: StepInput, run_context: RunContext) -> StepOutput:
    state = run_context.session_state
    narrative = Narrative.model_validate(state["narrative"])
    narrative.actions.extend(state["extra_actions"])
    state["revision"] = state.get("revision", 0) + 1
    report = render_report(state["evidence"], narrative, state["revision"])
    save_local_report(f"wf-{run_context.session_id}", state["revision"], report)
    state["report"] = report
    return StepOutput(content=report)


# ---------------------------------------------------------------- ráp workflow
def writer_agent() -> Agent:
    return Agent(
        id="workflow-writer",
        name="Workflow Writer",
        model=model(),
        output_schema=Narrative,
        instructions=[WRITER, "Chỉ dùng số trong evidence. Viết tiếng Việt."],
    )


def build_workflow() -> Workflow:
    # Dựng nhánh TRONG hàm: mỗi workflow có agent riêng, và không cần MODEL_ID lúc import module.
    numbers_branch = Step(name="numbers_only", executor=numbers_only)
    full_branch = Steps(
        name="full",
        steps=[
            Loop(
                name="draft",
                steps=[
                    Step(name="prompt", executor=make_writer_prompt),
                    Step(name="write", agent=writer_agent()),
                    Step(name="gate", executor=gate),
                ],
                end_condition=gate_passed,
                max_iterations=MAX_DRAFTS,
            ),
            Step(name="ensure_passed", executor=ensure_passed),
            Condition(name="alerts", evaluator=has_alerts, steps=[Step(name="escalate", executor=escalate)]),
        ],
    )

    def pick_branch(step_input: StepInput) -> Step | Steps:
        """Router: hàm chọn nhánh chạy tiếp (có thể trả nhiều nhánh)."""
        return numbers_branch if "chỉ số liệu" in request_of(step_input).instruction.lower() else full_branch

    return Workflow(
        id="report-workflow",
        name="Report Workflow",
        db=db(),
        input_schema=ReportRequest,
        session_state={"revision": 0},
        steps=[
            Parallel(
                Step(name="current", executor=fetch_current),
                Step(name="previous", executor=fetch_previous),
                name="gather",
            ),
            Step(name="evidence", executor=build_evidence),
            Router(name="mode", selector=pick_branch, choices=[numbers_branch, full_branch]),
            Step(
                name="publish",
                executor=publish,
                human_review=HumanReview(requires_confirmation=True, confirmation_message="Lưu báo cáo này?"),
            ),
        ],
    )


if __name__ == "__main__":
    session_id, quarter, instruction = sys.argv[1:4]
    workflow = build_workflow()
    run = workflow.run(input=ReportRequest(quarter=quarter, instruction=instruction), session_id=session_id)
    while run.is_paused:
        for requirement in run.active_step_requirements:
            answer = input(f"{requirement.confirmation_message} [y/N] ")
            requirement.confirm() if answer.lower() == "y" else requirement.reject("Người duyệt từ chối")
        run = workflow.continue_run(run_response=run)
    print(run.status.value)
    print(run.content)
