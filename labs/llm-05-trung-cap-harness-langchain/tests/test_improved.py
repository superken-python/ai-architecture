"""Các lớp cải tiến theo Claude Code: mỗi test kiểm một hành vi."""

from __future__ import annotations

import os
import time

from eval_golden import CASES, report, run
from harness.agent import build_agent
from harness.context import AgentContext
from harness.data import CustomerDB
from harness.improved import (
    ReminderMiddleware,
    RulesFileMiddleware,
    build_improved_agent,
    make_subagent_tool,
)
from harness.model import ScriptedChatModel, call, say
from harness.run import ask
from langchain.agents.middleware import ClearToolUsesEdit, ContextEditingMiddleware, SummarizationMiddleware
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver


def improved(model, db=None, **kwargs):
    kwargs.setdefault("approve_writes", False)  # tắt người duyệt để test tập trung vào lớp đang kiểm
    return build_improved_agent(model, db=db or CustomerDB(), checkpointer=InMemorySaver(), **kwargs)


def tool_texts(out) -> list[str]:
    return [m.text for m in out["messages"] if isinstance(m, ToolMessage)]


UPDATE = {"customer_id": "KH-0012", "field": "status", "value": "Hoàn tất"}


# ---------------------------------------------------------------- 1. File luật
def test_rules_file_is_appended_and_reloaded(tmp_path, thread):
    rules = tmp_path / "rules.md"
    rules.write_text("- Mã KH có dạng KH-0000", encoding="utf-8")
    model = ScriptedChatModel(steps=[say("ok"), say("ok")])
    agent = build_agent(
        model, db=CustomerDB(), checkpointer=InMemorySaver(), extra_middleware=[RulesFileMiddleware(rules)]
    )
    ask(agent, "a", thread=thread)
    assert "<project_rules>\n- Mã KH có dạng KH-0000\n</project_rules>" in model.calls[0][0].text
    time.sleep(0.01)
    rules.write_text("- Luật mới", encoding="utf-8")
    os.utime(rules, (time.time() + 5, time.time() + 5))  # bảo đảm mtime đổi trên mọi hệ file
    ask(agent, "b", thread=thread)
    assert "- Luật mới" in model.calls[1][0].text


# ---------------------------------------------------------------- 2. Đọc trước khi ghi
def test_write_without_read_is_blocked(thread):
    db = CustomerDB()
    model = ScriptedChatModel(steps=[call("update_customer", **UPDATE), say("Tôi sẽ đọc trước.")])
    out = ask(improved(model, db), "Đổi KH-0012 thành Hoàn tất", thread=thread)
    assert db.writes == []
    assert tool_texts(out) == ["Chặn: chưa đọc KH-0012 trong cuộc trò chuyện này. Đọc dữ liệu hiện tại trước khi ghi."]


def test_write_after_read_is_allowed_and_verified(thread):
    db = CustomerDB()
    model = ScriptedChatModel(
        steps=[call("search_customers", query="KH-0012"), call("update_customer", **UPDATE), say("Xong.")]
    )
    out = ask(improved(model, db), "Đổi KH-0012 thành Hoàn tất", thread=thread)
    assert db.writes == [("KH-0012", "status", "Hoàn tất")]
    assert tool_texts(out)[-1] == "Đã cập nhật KH-0012.status = Hoàn tất\nKiểm tra lại: OK, dữ liệu nguồn khớp."


def test_write_blocked_when_data_changed_after_read(thread):
    db = CustomerDB()
    model = ScriptedChatModel(
        steps=[
            call("search_customers", query="KH-0012"),
            say("Đã xem."),
            call("update_customer", **UPDATE),
            say("Tôi sẽ đọc lại."),
        ]
    )
    agent = improved(model, db)
    ask(agent, "Xem KH-0012", thread=thread)
    db.update("KH-0012", "debt", "0")  # người khác sửa dữ liệu giữa hai lượt
    out = ask(agent, "Đổi thành Hoàn tất", thread=thread)
    assert db.get("KH-0012")["status"] == "Đang giao"
    assert tool_texts(out)[-1] == "Chặn: KH-0012 đã thay đổi sau lần đọc trước. Đọc lại rồi mới ghi."


# ---------------------------------------------------------------- 3. Kiểm chứng sau khi ghi
class SilentlyBrokenDB(CustomerDB):
    def update(self, customer_id: str, field: str, value: str) -> None:
        self.writes.append((customer_id, field, value))  # báo thành công nhưng không ghi gì


def test_verify_after_write_catches_silent_failure(thread):
    model = ScriptedChatModel(
        steps=[call("search_customers", query="KH-0012"), call("update_customer", **UPDATE), say("…")]
    )
    out = ask(improved(model, SilentlyBrokenDB()), "Đổi KH-0012", thread=thread)
    assert tool_texts(out)[-1].endswith("Kiểm tra lại: SAI — status hiện là 'Đang giao', không phải 'Hoàn tất'")


# ---------------------------------------------------------------- 4. Nhắc trạng thái
def test_reminder_is_sent_to_model_but_not_stored(thread):
    model = ScriptedChatModel(steps=[call("search_customers", query="Hà Nội"), say("ok")])
    agent = build_agent(
        model,
        db=CustomerDB(),
        checkpointer=InMemorySaver(),
        extra_middleware=[ReminderMiddleware(lambda req: "Còn 7 lượt tool.")],
    )
    out = ask(agent, "Khách Hà Nội", thread=thread)
    last = model.calls[1][-1]
    assert isinstance(last, HumanMessage) and last.text == "<system-reminder>Còn 7 lượt tool.</system-reminder>"
    assert not any("system-reminder" in m.text for m in out["messages"])  # state sạch


# ---------------------------------------------------------------- 5. Chính sách quyền
def test_viewer_cannot_write(thread):
    db = CustomerDB()
    model = ScriptedChatModel(
        steps=[call("search_customers", query="KH-0012"), call("update_customer", **UPDATE), say("…")]
    )
    out = ask(improved(model, db), "Đổi", thread=thread, ctx=AgentContext(user_id="u1", role="viewer"))
    assert db.writes == []
    assert tool_texts(out)[-1].startswith("Không được phép: vai trò 'viewer'")


# ---------------------------------------------------------------- 6. Subagent
def test_subagent_returns_only_its_final_answer(thread):
    db = CustomerDB()
    from harness.tools import make_server_tools

    sub_model = ScriptedChatModel(
        steps=[call("search_customers", query="Hà Nội"), say("Hà Nội có 2 khách: KH-0012, KH-0047.")]
    )
    research = make_subagent_tool(
        "research_customers",
        "Tra cứu nhiều bước về khách hàng, trả lại bản tóm tắt.",
        sub_model,
        make_server_tools(db)[:1],
        "Bạn tra cứu khách hàng, trả lời ngắn.",
    )
    main = ScriptedChatModel(steps=[call("research_customers", task="Khách hàng ở Hà Nội"), say("Có 2 khách.")])
    ask(improved(main, db, subagents=[research]), "Ai ở Hà Nội?", thread=thread)
    seen_by_main = [m for m in main.calls[1] if isinstance(m, ToolMessage)]
    assert [m.text for m in seen_by_main] == ["Hà Nội có 2 khách: KH-0012, KH-0047."]
    assert not any("Công ty An Phát" in m.text for m in seen_by_main)  # kết quả thô của agent con không lọt ra


# ---------------------------------------------------------------- 7. Lập kế hoạch
def test_todo_middleware_adds_write_todos_tool(thread):
    model = ScriptedChatModel(steps=[say("ok")])
    ask(improved(model, todo=True), "a", thread=thread)
    assert "write_todos" in model.bound_tools[-1]


# ---------------------------------------------------------------- 8. Quản lý ngữ cảnh
def test_context_editing_clears_old_tool_results(thread):
    steps = [call("search_customers", query=q) for q in ["KH-0012", "KH-0031", "KH-0047", "Hà Nội"]] + [say("ok")]
    model = ScriptedChatModel(steps=steps)
    editing = ContextEditingMiddleware(edits=[ClearToolUsesEdit(trigger=200, keep=1)])
    ask(
        build_agent(model, db=CustomerDB(), checkpointer=InMemorySaver(), extra_middleware=[editing]),
        "a",
        thread=thread,
    )
    last_seen = [m.text for m in model.calls[-1] if isinstance(m, ToolMessage)]
    assert last_seen[:-1] == ["[cleared]"] * (len(last_seen) - 1)  # chỉ giữ kết quả mới nhất
    assert "KH-0012" in last_seen[-1]


def test_summarization_replaces_old_turns(thread):
    model = ScriptedChatModel(steps=[say(f"trả lời {i}") for i in range(4)])
    summarizer = ScriptedChatModel(steps=[say("TÓM TẮT: Lan hỏi về KH-0012.")] * 3)
    summary = SummarizationMiddleware(summarizer, trigger=("messages", 5), keep=("messages", 2))
    agent = build_agent(model, db=CustomerDB(), checkpointer=InMemorySaver(), extra_middleware=[summary])
    for i in range(4):
        ask(agent, f"câu {i}", thread=thread)
    assert summarizer.calls, "đã phải tóm tắt"
    assert any("TÓM TẮT: Lan hỏi về KH-0012." in m.text for m in model.calls[-1])
    assert not any(m.text == "câu 0" for m in model.calls[-1])  # lượt cũ đã được thay bằng bản tóm tắt


# ---------------------------------------------------------------- 9. Bộ đo vàng
def test_golden_eval_runner_scores_scripted_answers():
    answers = iter(
        [
            [call("search_customers", query="KH-0012"), say("ok")],
            [call("search_customers", query="Đà Nẵng"), say("ok")],
            [call("update_customer", **UPDATE)],  # sai luật: ghi trước khi tra cứu
            [say("Chào bạn!")],
        ]
    )

    def make_agent():
        return build_agent(ScriptedChatModel(steps=next(answers)), db=CustomerDB(), checkpointer=InMemorySaver())

    results = run(make_agent, CASES)
    assert [r.passed for r in results] == [True, True, False, True]
    assert report(results).startswith("Đạt 3/4")
