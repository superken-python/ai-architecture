from agno_lab.p04_session import build_agent, chat, show
from mock_llm import answer_json, call, say

SUMMARY = "Analyze the following conversation between a user and an assistant"  # system prompt lượt tóm tắt


def system_prompt(request: dict) -> str:
    return next(m["content"] for m in request["messages"] if m["role"] in ("system", "developer"))


def users(request: dict) -> list[str]:
    return [m["content"] for m in request["messages"] if m["role"] == "user"]


def script_summaries(llm, *texts):
    llm.script(*[answer_json({"summary": t, "topics": ["báo cáo"]}) for t in texts], match=SUMMARY)


def test_state_persists_across_runs_and_instances(llm):
    llm.script(call("record_revision", quarter="2026-Q2", note="bản đầu"), say("Đã viết v1."))
    llm.script(call("record_revision", quarter="2026-Q2", note="rút gọn"), say("Đã viết v2."))
    script_summaries(llm, "Lập báo cáo Q2.", "Rút gọn báo cáo Q2.")

    chat("report-01", "lan", "Lập báo cáo Q2")
    run = chat("report-01", "lan", "Rút tóm tắt còn 3 ý")  # mỗi lần chat là một Agent mới, như một process mới
    assert run.session_state["revision"] == 2
    assert run.session_state["notes"] == ["v1: bản đầu", "v2: rút gọn"]
    main = [r for r in llm.requests if SUMMARY not in system_prompt(r)]
    assert "Phiên bản hiện tại: v1, quý 2026-Q2." in system_prompt(main[2])  # instructions đọc từ state


def test_history_is_per_session(llm):
    llm.script(say("A1"), say("A2"), say("B1"))
    script_summaries(llm, "s1", "s1b", "s2")
    chat("report-01", "lan", "câu 1")
    chat("report-01", "lan", "câu 2")
    chat("report-02", "lan", "câu khác")
    main = [r for r in llm.requests if SUMMARY not in system_prompt(r)]
    assert users(main[1]) == ["câu 1", "câu 2"]  # run 2 thấy run 1
    assert users(main[2]) == ["câu khác"]  # session khác không thấy gì


def test_summary_is_an_extra_model_call_and_goes_into_context(llm):
    llm.script(say("A1"), say("A2"))
    script_summaries(llm, "Lan lập báo cáo Q2.", "Lan sửa báo cáo Q2.")
    chat("report-01", "lan", "câu 1")
    assert len(llm.requests) == 2  # 1 lượt trả lời + 1 lượt tóm tắt
    chat("report-01", "lan", "câu 2")
    main = [r for r in llm.requests if SUMMARY not in system_prompt(r)]
    assert "Lan lập báo cáo Q2." in system_prompt(main[1])
    assert "summary: Lan sửa báo cáo Q2." in show("report-01")


def test_agentic_state_adds_update_tool(llm):
    llm.script(say("ok"))
    script_summaries(llm, "x")
    build_agent(agentic_state=True).run("chào", session_id="s", user_id="u")
    assert "update_session_state" in [t["function"]["name"] for t in llm.requests[0]["tools"]]
