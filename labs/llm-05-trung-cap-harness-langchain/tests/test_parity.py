"""Harness LangChain tái hiện đúng hành vi đã đo trên Agno 3.1.3 (và chỗ cố ý khác)."""

from __future__ import annotations

import asyncio

from harness.agent import build_agent
from harness.context import AgentContext
from harness.data import CustomerDB
from harness.model import ScriptedChatModel, call, say
from harness.run import ask, pending, resume
from langchain.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore


def counting_echo():
    counter = {"n": 0}

    @tool
    def echo(x: str) -> str:
        """Trả lại x."""
        counter["n"] += 1
        return f"echo:{x}"

    return echo, counter


def agent_with(model, **kwargs):
    kwargs.setdefault("db", CustomerDB())
    kwargs.setdefault("checkpointer", InMemorySaver())
    return build_agent(model, **kwargs)


# ---------------------------------------------------------------- Thí nghiệm 1: giới hạn tool
def test_tool_limit_continue_behaves_like_agno():
    """exit_behavior="continue": vượt giới hạn chỉ trả lỗi cho từng lượt, vòng lặp chạy tới khi model ngừng."""
    echo, counter = counting_echo()
    model = ScriptedChatModel(steps=[call("echo", x=str(i)) for i in range(8)] + [say("xong")])
    agent = agent_with(model, extra_tools=[echo], tool_call_limit=2, limit_exit="continue", model_call_limit=50)
    out = ask(agent, "thử")
    assert counter["n"] == 2
    assert len(model.calls) == 9  # đúng như Agno: 8 lượt gọi tool + 1 lượt trả lời
    assert out["messages"][-1].content == "xong"


def test_tool_limit_end_stops_the_loop():
    """exit_behavior="end": dừng ngay ở lượt vượt giới hạn — guard mà Agno không có."""
    echo, counter = counting_echo()
    model = ScriptedChatModel(steps=[call("echo", x=str(i)) for i in range(8)] + [say("xong")])
    agent = agent_with(model, extra_tools=[echo], tool_call_limit=2, limit_exit="end")
    out = ask(agent, "thử")
    assert counter["n"] == 2
    assert len(model.calls) == 3
    assert isinstance(out["messages"][-1], AIMessage) and not out["messages"][-1].tool_calls


def test_model_call_limit_caps_runaway_loop():
    echo, _ = counting_echo()
    model = ScriptedChatModel(steps=[call("echo", x=str(i)) for i in range(20)])
    agent = agent_with(model, extra_tools=[echo], tool_call_limit=100, model_call_limit=4)
    ask(agent, "thử")
    assert len(model.calls) == 4


# ---------------------------------------------------------------- Thí nghiệm 3: cửa sổ lịch sử
def humans_seen(call_messages) -> list[str]:
    return [m.text for m in call_messages if isinstance(m, HumanMessage)]


def test_history_window_default_three_runs(thread):
    model = ScriptedChatModel(steps=[say(f"trả lời {i}") for i in range(5)])
    agent = agent_with(model)  # num_history_runs mặc định 3, giống Agno
    for i in range(5):
        ask(agent, f"câu hỏi {i}", thread=thread)
    assert humans_seen(model.calls[-1]) == ["câu hỏi 1", "câu hỏi 2", "câu hỏi 3", "câu hỏi 4"]


def test_history_window_two_runs(thread):
    model = ScriptedChatModel(steps=[say(f"trả lời {i}") for i in range(5)])
    agent = agent_with(model, num_history_runs=2)
    for i in range(5):
        ask(agent, f"câu hỏi {i}", thread=thread)
    assert humans_seen(model.calls[-1]) == ["câu hỏi 2", "câu hỏi 3", "câu hỏi 4"]


# ---------------------------------------------------------------- Thí nghiệm 2 + 5 run: memory
def memory_agent(main_steps, memory_steps, **kwargs):
    main, memory, store = ScriptedChatModel(steps=main_steps), ScriptedChatModel(steps=memory_steps), InMemoryStore()
    agent = agent_with(main, store=store, memory_model=memory, **kwargs)
    return agent, main, memory, store


def memories(store, user_id="u1"):
    return [it.value["memory"] for it in store.search(("memories", user_id))]


def test_memory_written_at_end_of_run_and_injected_next_run(thread):
    agent, main, memory, store = memory_agent(
        [say("Đã ghi nhận."), say("Chào Lan.")],
        [call("add_memory", memory="Tên Lan, hay lọc theo Hà Nội"), say("ok"), say("không có")],
    )
    ask(agent, "Tôi là Lan, hay lọc theo Hà Nội", thread=thread)
    assert memories(store) == ["Tên Lan, hay lọc theo Hà Nội"]  # đã có ngay khi invoke trả về
    # Trình trích xuất chỉ thấy system + tin nhắn user, giống Agno
    extractor_input = memory.calls[0]
    assert [type(m) for m in extractor_input] == [SystemMessage, HumanMessage]
    assert extractor_input[1].text == "Người dùng: Tôi là Lan, hay lọc theo Hà Nội"

    ask(agent, "Chào", thread=thread)
    assert "memories_from_previous_interactions" not in main.calls[0][0].text  # run 1: chưa có memory
    assert "Tên Lan, hay lọc theo Hà Nội" in main.calls[1][0].text  # run 2: memory ở cuối system prompt


def test_memory_skipped_without_user_id(thread):
    agent, _, memory, store = memory_agent([say("Chào.")], [])
    ask(agent, "Tôi là Lan", thread=thread, ctx=AgentContext(user_id=None))
    assert memory.calls == [] and store.search(("memories",)) == []  # Agno sẽ ghi vào user "default"


def test_five_runs_match_agno_experiment(thread):
    agent, main, _, store = memory_agent(
        [
            say("Đã ghi nhận, Lan."),
            call("search_customers", query="KH-0012"),
            say("KH-0012 còn 180 triệu."),
            say("Còn 180 triệu."),
            say("Lọc theo Hà Nội."),
            say("KH-0012, KH-0047."),
        ],
        [call("add_memory", memory="Tên Lan, hay lọc theo Hà Nội"), say("ok")] + [say("không có")] * 4,
    )
    questions = [
        "Tôi là Lan, hay lọc theo Hà Nội",
        "Tra KH-0012",
        "Còn hạn mức không?",
        "Lọc như mọi khi",
        "Khách hàng khu vực tôi",
    ]
    seen = []
    for q in questions:
        before = len(main.calls)
        ask(agent, q, thread=thread)
        seen.append(main.calls[before])  # lượt model đầu tiên của mỗi run
    has_memory = ["memories_from_previous" in s[0].text for s in seen]
    assert has_memory == [False, True, True, True, True]
    assert humans_seen(seen[2]) == questions[:3]  # run 3 thấy run 1–2
    assert any(isinstance(m, ToolMessage) and "KH-0012" in m.text for m in seen[2])  # kết quả tool run 2 vẫn còn
    assert humans_seen(seen[4]) == questions[1:5]  # run 5: run 1 đã ra khỏi cửa sổ...
    assert memories(store) == ["Tên Lan, hay lọc theo Hà Nội"]  # ...nhưng memory vẫn giữ điều Lan nói ở run 1


# ---------------------------------------------------------------- Tạm dừng / chạy tiếp
def test_client_tool_pauses_and_resumes(thread):
    model = ScriptedChatModel(steps=[call("excel_read_rows", rows=[2, 3]), say("Dòng 2 là KH-0012.")])
    agent = agent_with(model)
    out = ask(agent, "Đọc dòng 2-3", thread=thread)
    (waiting,) = pending(out)
    assert waiting["type"] == "client_tool"
    assert waiting["name"] == "excel_read_rows" and waiting["args"] == {"rows": [2, 3]}
    # Client (add-in) chạy Office.js rồi gửi kết quả về
    out = resume(agent, {"2": ["KH-0012", "An Phát"]}, thread=thread)
    tool_msg = next(m for m in out["messages"] if isinstance(m, ToolMessage))
    assert tool_msg.text == '{"2": ["KH-0012", "An Phát"]}'
    assert out["messages"][-1].content == "Dòng 2 là KH-0012."


def test_write_needs_approval_then_approve_or_reject(thread):
    db = CustomerDB()
    model = ScriptedChatModel(
        steps=[
            call("update_customer", customer_id="KH-0012", field="status", value="Hoàn tất"),
            say("Đã cập nhật."),
            call("update_customer", customer_id="KH-0031", field="status", value="Tạm dừng"),
            say("Đã huỷ."),
        ]
    )
    agent = agent_with(model, db=db)
    out = ask(agent, "Đổi KH-0012 thành Hoàn tất", thread=thread)
    (request,) = pending(out)
    assert request["action_requests"][0]["name"] == "update_customer"
    assert db.writes == []  # chưa duyệt thì chưa ghi
    resume(agent, {"decisions": [{"type": "approve"}]}, thread=thread)
    assert db.writes == [("KH-0012", "status", "Hoàn tất")]

    ask(agent, "Đổi KH-0031 thành Tạm dừng", thread=thread)
    out = resume(agent, {"decisions": [{"type": "reject", "message": "Không đổi"}]}, thread=thread)
    assert db.writes == [("KH-0012", "status", "Hoàn tất")]
    assert any(isinstance(m, ToolMessage) and "Không đổi" in m.text for m in out["messages"])


# ---------------------------------------------------------------- Async + lưu bền
def test_async_invoke_runs_same_middlewares(thread):
    agent, main, _, store = memory_agent(
        [say("Đã ghi nhận."), say("Chào Lan.")], [call("add_memory", memory="Tên Lan"), say("ok"), say("không có")]
    )

    async def scenario():
        for text in ["Tôi là Lan", "Chào"]:
            await agent.ainvoke(
                {"messages": [{"role": "user", "content": text}]},
                {"configurable": {"thread_id": thread}},
                context=AgentContext(user_id="u1"),
            )

    asyncio.run(scenario())
    assert memories(store) == ["Tên Lan"]
    assert "Tên Lan" in main.calls[1][0].text


def test_sqlite_checkpointer_survives_restart(tmp_path, thread):
    path = str(tmp_path / "threads.db")
    with SqliteSaver.from_conn_string(path) as saver:
        agent_with(ScriptedChatModel(steps=[say("Đã ghi nhận.")]), checkpointer=saver).invoke(
            {"messages": [{"role": "user", "content": "Tôi là Lan"}]},
            {"configurable": {"thread_id": thread}},
            context=AgentContext(user_id="u1"),
        )
    model = ScriptedChatModel(steps=[say("Bạn là Lan.")])
    with SqliteSaver.from_conn_string(path) as saver:  # "khởi động lại" tiến trình
        agent_with(model, checkpointer=saver).invoke(
            {"messages": [{"role": "user", "content": "Tôi là ai?"}]},
            {"configurable": {"thread_id": thread}},
            context=AgentContext(user_id="u1"),
        )
    assert humans_seen(model.calls[0]) == ["Tôi là Lan", "Tôi là ai?"]
