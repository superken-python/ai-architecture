import pytest

from agno_lab.p05_memory import ask, build_agent, memories
from mock_llm import call, say

MEMORY = "You are a Memory Manager"  # system prompt của trình trích xuất memory trong Agno 3.1.3


def roles(request: dict) -> list[str]:
    return [m["role"] for m in request["messages"]]


def test_automatic_memory_crosses_sessions(llm):
    llm.script(say("Chào Lan."), say("Báo cáo ngắn cho khối Cloud."))
    llm.script(
        call("add_memory", memory="Tên Lan, phụ trách khối Cloud, thích báo cáo ngắn"),
        say("ok"),
        say("không có"),
        match=MEMORY,
    )
    ask("lan", "Tôi là Lan, phụ trách khối Cloud, thích báo cáo ngắn", session_id="s1")
    assert memories("lan") == ["Tên Lan, phụ trách khối Cloud, thích báo cáo ngắn"]

    ask("lan", "Tóm tắt KPI cho tôi", session_id="s2")  # session MỚI, không có lịch sử
    main = [r for r in llm.requests if MEMORY not in r["messages"][0]["content"]]
    assert "phụ trách khối Cloud" in main[1]["messages"][0]["content"]  # memory nằm trong system prompt
    extractor = llm.requests_for(MEMORY)[0]
    assert "KHÔNG nhớ số liệu KPI" in extractor["messages"][0]["content"]  # luật CAPTURE của ta
    assert "assistant" not in roles(extractor)  # trình trích xuất chỉ thấy tin nhắn user


def test_memory_is_per_user(llm):
    llm.script(say("ok"))
    llm.script(call("add_memory", memory="Tên Lan"), say("ok"), match=MEMORY)
    ask("lan", "Tôi là Lan")
    assert memories("lan") == ["Tên Lan"] and memories("minh") == []


def test_missing_user_id_is_refused_and_agno_default_shows_why(llm):
    with pytest.raises(ValueError, match="user_id"):
        ask(None, "Tôi là Lan")
    llm.script(say("ok"))
    llm.script(call("add_memory", memory="Tên Lan"), say("ok"), match=MEMORY)
    build_agent().run("Tôi là Lan", session_id="s")  # gọi Agno trực tiếp, không user_id
    assert memories("default") == ["Tên Lan"]  # mọi người ẩn danh dùng chung bucket này


def test_agentic_memory_lets_the_agent_decide(llm):
    llm.script(call("update_user_memory", task="Lưu: Lan phụ trách khối Cloud"), say("Đã ghi nhớ."))
    llm.script(call("add_memory", memory="Lan phụ trách khối Cloud"), say("ok"), match=MEMORY)
    run = ask("lan", "Nhớ giúp: tôi phụ trách khối Cloud", agentic=True)
    assert [t.tool_name for t in run.tools] == ["update_user_memory"]
    assert memories("lan") == ["Lan phụ trách khối Cloud"]
