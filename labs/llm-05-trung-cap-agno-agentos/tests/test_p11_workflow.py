import json

import pytest

from agno_lab.p02_structured import ReportRequest
from agno_lab.p11_workflow import WRITER, build_workflow
from mock_llm import answer_json
from settings_paths import clean_storage, storage_file

GOOD = {
    "executive_summary": ["CLOUD_OPS chi phí tăng 18%.", "FIN_TECH doanh thu giảm 12,5%."],
    "actions": ["Rà soát chi phí."],
}
MISSES_FINTECH = {"executive_summary": ["CLOUD_OPS chi phí tăng."], "actions": ["x"]}
REQUEST = ReportRequest(quarter="2026-Q2", instruction="Lập báo cáo, nêu rủi ro")


@pytest.fixture(autouse=True)
def _clean():
    for session in ("w1", "w2", "w3", "w4", "w5", "w6"):
        clean_storage(f"wf-{session}")


def approve_all(workflow, run):
    while run.is_paused:
        for requirement in run.active_step_requirements:
            requirement.confirm()
        run = workflow.continue_run(run_response=run)
    return run


def writer_prompts(llm) -> list[str]:
    return [json.dumps(r["messages"], ensure_ascii=False) for r in llm.requests_for(WRITER)]


def test_full_branch_retries_with_feedback_then_waits_for_review(llm):
    llm.script(answer_json(MISSES_FINTECH), answer_json(GOOD), match=WRITER)
    workflow = build_workflow()
    run = workflow.run(input=REQUEST, session_id="w1")
    assert run.is_paused and run.paused_step_name == "publish"
    assert not storage_file("wf-w1", "v1.md").exists()  # chưa duyệt thì chưa lưu

    prompts = writer_prompts(llm)
    assert len(prompts) == 2 and "Tóm tắt chưa nhắc FIN_TECH" in prompts[1]  # lần 2 nhận nhận xét của cổng
    final = approve_all(workflow, run)
    assert final.status.value == "COMPLETED"
    report = storage_file("wf-w1", "v1.md").read_text(encoding="utf-8")
    assert "| KPI_02 | CẢNH BÁO VÀNG |" in report and "Họp xử lý cảnh báo với CLOUD_OPS, FIN_TECH" in report
    state = workflow.get_session_state(session_id="w1")
    assert state["revision"] == 1 and state["attempt"] == 2


def test_exhausted_drafts_stop_the_workflow(llm):
    llm.script(*[answer_json(MISSES_FINTECH)] * 3, match=WRITER)
    workflow = build_workflow()
    run = workflow.run(input=REQUEST, session_id="w2")
    assert not run.is_paused and len(writer_prompts(llm)) == 3
    assert "không qua cổng sau 3 lần" in str(run.content)
    assert not storage_file("wf-w2", "v1.md").exists()
    assert workflow.get_session_state(session_id="w2")["revision"] == 0


def test_router_numbers_only_skips_the_llm(llm):
    workflow = build_workflow()
    run = workflow.run(input=ReportRequest(quarter="2026-Q2", instruction="Chỉ số liệu thôi"), session_id="w3")
    final = approve_all(workflow, run)
    assert llm.requests == []  # không gọi model lần nào
    assert "Báo cáo chỉ gồm số liệu." in storage_file("wf-w3", "v1.md").read_text(encoding="utf-8")
    assert final.status.value == "COMPLETED"


def test_rejected_review_skips_publishing(llm):
    llm.script(answer_json(GOOD), match=WRITER)
    workflow = build_workflow()
    run = workflow.run(input=REQUEST, session_id="w4")
    for requirement in run.active_step_requirements:
        requirement.reject("Chưa đủ ý")
    final = workflow.continue_run(run_response=run)
    assert final.status.value == "COMPLETED" and not storage_file("wf-w4", "v1.md").exists()
    assert workflow.get_session_state(session_id="w4")["revision"] == 0


def test_second_run_in_same_session_makes_v2_from_v1(llm):
    llm.script(answer_json(GOOD), answer_json(GOOD), match=WRITER)
    workflow = build_workflow()
    approve_all(workflow, workflow.run(input=REQUEST, session_id="w5"))
    approve_all(workflow, workflow.run(input=ReportRequest(quarter="2026-Q2", instruction="Rút gọn"), session_id="w5"))
    assert storage_file("wf-w5", "v2.md").exists()
    assert "# Báo cáo v1" in writer_prompts(llm)[1]  # lần 2 viết dựa trên báo cáo v1


def test_continue_from_a_new_instance_by_run_id(llm):
    llm.script(answer_json(GOOD), match=WRITER)
    paused = build_workflow().run(input=REQUEST, session_id="w6")
    requirements = paused.step_requirements
    for requirement in requirements:
        requirement.confirm()
    final = build_workflow().continue_run(run_id=paused.run_id, session_id="w6", step_requirements=requirements)
    assert final.status.value == "COMPLETED" and storage_file("wf-w6", "v1.md").exists()
