from fastapi.testclient import TestClient

from agno_lab.p01_agent import build_agent
from agno_lab.p12_os import build_os
from agno_lab.p16_evals import QUESTION, accuracy, judge, performance, reliability, suite
from mock_llm import answer_json, call, say

ANALYST = "Luôn lấy số liệu bằng get_quarter_kpis"
ACCURACY_JUDGE = "You are an expert judge tasked with comparing"  # system prompt giám khảo của AccuracyEval
CRITERIA_JUDGE = "You are an expert evaluator."  # system prompt giám khảo của AgentAsJudgeEval


def test_reliability_checks_tool_and_arguments_without_a_judge(llm):
    llm.script(
        call("get_quarter_kpis", quarter="2026-Q2"), say("ok"),  # run 1: đúng quý
        call("get_quarter_kpis", quarter="2026-Q1"), say("ok"),  # run 2: sai quý
        match=ANALYST,
    )  # fmt: skip
    good = reliability(build_agent().run(QUESTION))
    assert good.eval_status == "PASSED" and good.passed_argument_checks == ["get_quarter_kpis"]
    wrong_quarter = reliability(build_agent().run(QUESTION))
    assert wrong_quarter.eval_status == "FAILED" and wrong_quarter.failed_argument_checks == ["get_quarter_kpis"]
    assert len(llm.requests) == 4  # chỉ có lượt gọi của agent, không có giám khảo


def test_accuracy_judge_compares_output_with_the_expected_answer(llm):
    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), say("CLOUD_OPS cảnh báo vàng."), match=ANALYST)
    llm.script(answer_json({"accuracy_score": 5, "accuracy_reason": "Thiếu FIN_TECH."}), match=ACCURACY_JUDGE)
    result = accuracy()
    assert result.avg_score == 5 and result.results[0].output == "CLOUD_OPS cảnh báo vàng."
    prompt = llm.requests_for(ACCURACY_JUDGE)[0]["messages"][-1]["content"]
    assert "<expected_output>" in prompt and "<agent_output>\nCLOUD_OPS cảnh báo vàng." in prompt
    assert "tối đa 5 điểm" in llm.requests_for(ACCURACY_JUDGE)[0]["messages"][0]["content"]  # guideline của ta


def test_criteria_judge_grades_any_output(llm):
    llm.script(answer_json({"passed": False, "reason": "Nhắc benchmark thị trường."}), match=CRITERIA_JUDGE)
    result = judge("CLOUD_OPS cao hơn benchmark thị trường 20%.")
    assert result.pass_rate == 0.0 and result.results[0].reason == "Nhắc benchmark thị trường."
    assert "không nhắc nguồn web" in llm.requests[0]["messages"][0]["content"]  # tiêu chí nằm trong system prompt


def test_performance_measures_a_function_without_the_model(llm):
    result = performance()
    assert len(result.run_times) == 20 and result.avg_run_time > 0
    assert llm.requests == []


def test_suite_returns_pass_or_fail_for_ci(llm):
    llm.script(
        call("get_quarter_kpis", quarter="2026-Q2"), say("CLOUD_OPS và FIN_TECH bị cảnh báo."),  # case 1
        call("get_quarter_kpis", quarter="2026-Q2"), say("Vì chi phí tăng."),  # case 2: quên inspect_rules
        match=ANALYST,
    )  # fmt: skip
    llm.script(answer_json({"passed": True, "reason": "Chỉ số liệu nội bộ."}), match=CRITERIA_JUDGE)
    result = suite().to_dict()
    assert result["summary"] == {"total": 2, "passed": 1, "failed": 1, "status": "FAIL"}
    second = result["cases"][1]
    assert second["reliability_passed"] is False and second["tools_called"] == ["get_quarter_kpis"]


def test_suite_can_run_one_tag(llm):
    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), say("CLOUD_OPS và FIN_TECH."), match=ANALYST)
    llm.script(answer_json({"passed": True, "reason": "ok"}), match=CRITERIA_JUDGE)
    assert suite(tag="smoke").status == "PASS"


def test_eval_runs_are_listed_by_agentos(llm):
    llm.script(answer_json({"passed": True, "reason": "ok"}), match=CRITERIA_JUDGE)
    judge("CLOUD_OPS và FIN_TECH bị cảnh báo.")
    performance()
    with TestClient(build_os(tracing=False).get_app()) as client:
        rows = client.get("/eval-runs").json()["data"]
    assert sorted((r["name"], r["eval_type"]) for r in rows) == [
        ("dung-agent", "performance"),
        ("khong-dung-nguon-ngoai", "agent_as_judge"),
    ]
