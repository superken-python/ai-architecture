import json

import pytest

from agno_lab.p02_structured import NarrativeInvalid, ReportRequest, build_report, build_writer, write_narrative
from mock_llm import answer_json, call
from reporting import Narrative

GOOD = {
    "executive_summary": ["Cloud tăng chi phí 18%.", "FinTech giảm doanh thu 12,5%."],
    "actions": ["Rà soát chi phí."],
}


def test_input_is_validated_before_any_model_call(llm):
    with pytest.raises(ValueError, match="quarter"):
        build_writer().run(input={"quarter": "Q2", "instruction": "lập báo cáo"})
    assert llm.requests == []  # không tốn lượt gọi model nào


def test_input_schema_becomes_json_user_message_and_output_is_typed(llm):
    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), answer_json(GOOD))
    narrative = write_narrative(ReportRequest(quarter="2026-Q2", instruction="Nêu hai rủi ro"))
    assert isinstance(narrative, Narrative) and narrative.actions == ["Rà soát chi phí."]
    user = next(m["content"] for m in llm.requests[0]["messages"] if m["role"] == "user")
    assert json.loads(user) == {"quarter": "2026-Q2", "instruction": "Nêu hai rủi ro"}
    fmt = llm.requests[0]["response_format"]
    assert fmt["type"] == "json_schema" and fmt["json_schema"]["name"] == "Narrative"


def test_invalid_output_is_not_silently_accepted(llm):
    llm.script(answer_json({"executive_summary": ["thiếu actions"]}))
    run = build_writer().run(input=ReportRequest(quarter="2026-Q2", instruction="lập báo cáo"))
    assert run.status.value == "COMPLETED" and isinstance(run.content, str)  # Agno coi là thành công!
    llm.script(answer_json({"executive_summary": ["thiếu actions"]}))
    with pytest.raises(NarrativeInvalid):
        write_narrative(ReportRequest(quarter="2026-Q2", instruction="lập báo cáo"))


def test_json_mode_for_models_without_json_schema(llm):
    llm.script(answer_json(GOOD))
    narrative = write_narrative(
        ReportRequest(quarter="2026-Q2", instruction="lập báo cáo"), agent=build_writer(json_mode=True)
    )
    assert narrative.executive_summary == GOOD["executive_summary"]
    assert llm.requests[0]["response_format"] == {"type": "json_object"}


def test_numbers_come_from_code_not_llm(llm):
    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), answer_json(GOOD))
    report = build_report(ReportRequest(quarter="2026-Q2", instruction="lập báo cáo"))
    assert "6.59%" in report and "| KPI_02 | CẢNH BÁO VÀNG |" in report
    assert "- Cloud tăng chi phí 18%." in report
