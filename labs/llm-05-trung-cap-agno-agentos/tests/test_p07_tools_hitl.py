import json

import pytest

from agno_lab import p07_tools_hitl as p7
from agno_lab.p07_tools_hitl import build_agent, resolve
from mock_llm import call, say
from settings_paths import clean_storage, storage_file

SAVE = {"report_id": "hitl-test", "revision": 1, "markdown": "# Báo cáo v1"}


@pytest.fixture(autouse=True)
def _clean():
    for report_id in ("hitl-test", "hitl-reject", "hitl-restart"):
        clean_storage(report_id)


def test_confirmation_pauses_then_runs_when_approved(llm):
    llm.script(call("save_report", **SAVE), say("Đã lưu báo cáo."))
    agent = build_agent()
    run = agent.run("Lưu báo cáo", session_id="s1")
    assert run.is_paused and run.status.value == "PAUSED"
    (req,) = run.active_requirements
    assert req.needs_confirmation and req.tool_execution.tool_name == "save_report"
    assert not storage_file("hitl-test", "v1.md").exists()  # chưa duyệt thì chưa chạy

    final = resolve(agent, run, lambda r: r.confirm())
    assert final.content == "Đã lưu báo cáo." and storage_file("hitl-test", "v1.md").exists()


def test_rejection_reaches_the_model(llm):
    llm.script(call("save_report", **{**SAVE, "report_id": "hitl-reject"}), say("Đã huỷ lưu."))
    agent = build_agent()
    final = resolve(agent, agent.run("Lưu", session_id="s2"), lambda r: r.reject("Chưa duyệt nội dung"))
    assert not storage_file("hitl-reject", "v1.md").exists()
    tool_msg = next(m["content"] for m in llm.requests[1]["messages"] if m["role"] == "tool")
    assert "Chưa duyệt nội dung" in tool_msg and final.content == "Đã huỷ lưu."


def test_user_input_fills_the_missing_field(llm):
    llm.script(call("assign_owner", action="Rà soát chi phí Cloud"), say("Đã giao việc."))
    agent = build_agent()
    run = agent.run("Giao việc rà soát chi phí", session_id="s3")
    schema = next(
        t["function"]["parameters"] for t in llm.requests[0]["tools"] if t["function"]["name"] == "assign_owner"
    )
    assert list(schema["properties"]) == ["action"]  # owner bị ẩn khỏi model: model không thể tự bịa người phụ trách
    (req,) = run.active_requirements
    assert req.needs_user_input
    missing = [f.name for f in req.user_input_schema if f.value is None]  # model đã điền action, thiếu owner
    assert missing == ["owner"]
    final = resolve(agent, run, lambda r: r.provide_user_input({"owner": "Trưởng khối Cloud"}))
    assert final.tools[-1].result == "Đã giao 'Rà soát chi phí Cloud' cho Trưởng khối Cloud"


def test_external_execution_result_comes_from_client(llm):
    rows = [{"dept": "CLOUD_OPS", "alert": "CẢNH BÁO VÀNG"}]
    llm.script(call("export_to_excel", sheet="KPI", rows=rows), say("Đã xuất 1 dòng."))
    agent = build_agent()
    run = agent.run("Xuất KPI ra Excel", session_id="s4")
    (req,) = run.active_requirements
    assert req.needs_external_execution and req.tool_execution.tool_args == {"sheet": "KPI", "rows": rows}
    final = resolve(agent, run, lambda r: r.set_external_execution_result(json.dumps({"written": 1})))
    assert final.content == "Đã xuất 1 dòng."
    tool_msg = next(m["content"] for m in llm.requests[1]["messages"] if m["role"] == "tool")
    assert json.loads(tool_msg) == {"written": 1}


def test_continue_from_a_new_process_using_run_id(llm):
    llm.script(call("save_report", **{**SAVE, "report_id": "hitl-restart"}), say("Đã lưu sau khi khởi động lại."))
    paused = build_agent().run("Lưu", session_id="s5")
    for req in paused.requirements:
        req.confirm()
    fresh = build_agent()  # như một process mới: không giữ RunOutput trong bộ nhớ, chỉ có run_id + DB
    final = fresh.continue_run(run_id=paused.run_id, session_id="s5", requirements=paused.requirements)
    assert final.content == "Đã lưu sau khi khởi động lại." and storage_file("hitl-restart", "v1.md").exists()


def test_hooks_cache_and_stop_after_tool_call(llm):
    p7.AUDIT.clear()
    llm.script(
        call("get_quarter_kpis", quarter="2026-Q2"),
        call("get_quarter_kpis", quarter="2026-Q2"),
        call("publish_notice", text="Báo cáo Q2 sẵn sàng"),
    )
    run = build_agent().run("Kiểm tra KPI rồi thông báo", session_id="s6")
    assert [a["tool"] for a in p7.AUDIT] == ["get_quarter_kpis", "get_quarter_kpis", "publish_notice"]
    first, second, notice = run.tools
    assert first.result == second.result  # lần 2 lấy từ cache của Toolkit
    assert run.content == "THÔNG BÁO: Báo cáo Q2 sẵn sàng" and len(llm.requests) == 3  # dừng ngay, không gọi model thêm
