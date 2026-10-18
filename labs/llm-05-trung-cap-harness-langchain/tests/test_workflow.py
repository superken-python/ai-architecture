"""Workflow thư nhắc nợ bằng StateGraph: cùng sáu tình huống với test workflow của Agno (Lab 01, Phần 11)."""

from __future__ import annotations

import sqlite3

from harness.data import CustomerDB
from harness.model import ScriptedChatModel, call
from harness.run import pending
from harness.workflow import MAX_DRAFTS, build_workflow, start
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

GOOD = {"subject": "Nhắc thanh toán công nợ", "body": "Kính gửi Hải Đăng, quý khách còn nợ 79.000.000 đồng."}
NO_AMOUNT = {"subject": "Nhắc thanh toán công nợ", "body": "Kính gửi Hải Đăng, mong quý khách sớm thanh toán."}


def letter(**fields) -> object:
    return call("Letter", **fields)


def flow(model, outbox, checkpointer=None):
    return build_workflow(model, CustomerDB(), outbox, checkpointer or InMemorySaver())


def approve(graph, thread: str, ok: bool = True) -> dict:
    return graph.invoke(Command(resume={"approve": ok}), {"configurable": {"thread_id": thread}})


def test_rewrites_with_feedback_then_waits_for_review():
    model, outbox = ScriptedChatModel(steps=[letter(**NO_AMOUNT), letter(**GOOD)]), []
    graph = flow(model, outbox)
    out = start(graph, "w1", "KH-0047", "Viết thư nhắc nợ")
    (review,) = pending(out)
    assert review["type"] == "review" and review["letter"] == GOOD and outbox == []  # chưa duyệt thì chưa gửi
    second_prompt = model.calls[1][-1].content
    assert "Thư chưa nêu đúng số tiền nợ 79.000.000 đồng" in second_prompt  # lần 2 nhận nhận xét của cổng
    assert review["escalation"].startswith("Báo trưởng phòng tín dụng")  # nợ 79/80 triệu > 90% hạn mức

    final = approve(graph, "w1")
    assert final["status"] == "sent" and final["revision"] == 1 and outbox[0]["subject"] == GOOD["subject"]


def test_draft_with_invalid_schema_counts_as_a_failed_attempt():
    model, outbox = ScriptedChatModel(steps=[letter(subject="x", body="ngắn"), letter(**GOOD)]), []
    out = start(flow(model, outbox), "w7", "KH-0047", "Viết thư nhắc nợ")
    assert pending(out)[0]["letter"] == GOOD and len(model.calls) == 2
    assert "Thư không đúng schema Letter" in model.calls[1][-1].content


def test_exhausted_drafts_stop_the_flow():
    model, outbox = ScriptedChatModel(steps=[letter(**NO_AMOUNT)] * MAX_DRAFTS), []
    out = start(flow(model, outbox), "w2", "KH-0047", "Viết thư nhắc nợ")
    assert out["status"] == "failed" and pending(out) == [] and len(model.calls) == MAX_DRAFTS and outbox == []


def test_numbers_only_route_skips_the_llm():
    model, outbox = ScriptedChatModel(steps=[]), []
    graph = flow(model, outbox)
    out = start(graph, "w3", "KH-0012", "Chỉ số liệu thôi")
    assert pending(out)[0]["letter"]["body"].endswith("120.000.000 đồng.") and model.calls == []
    assert pending(out)[0]["escalation"] is None  # 120/300 triệu: không vượt 90% hạn mức
    assert approve(graph, "w3")["status"] == "sent"


def test_rejected_review_sends_nothing():
    model, outbox = ScriptedChatModel(steps=[letter(**GOOD)]), []
    graph = flow(model, outbox)
    start(graph, "w4", "KH-0047", "Viết thư nhắc nợ")
    final = approve(graph, "w4", ok=False)
    assert final["status"] == "rejected" and outbox == [] and final.get("revision", 0) == 0


def test_second_run_on_the_same_thread_builds_on_the_first():
    model, outbox = ScriptedChatModel(steps=[letter(**GOOD), letter(**{**GOOD, "subject": "Nhắc nợ lần hai"})]), []
    graph = flow(model, outbox)
    start(graph, "w5", "KH-0047", "Viết thư nhắc nợ")
    approve(graph, "w5")
    start(graph, "w5", "KH-0047", "Viết lại, giọng cứng rắn hơn")
    final = approve(graph, "w5")
    assert final["revision"] == 2 and [m["revision"] for m in outbox] == [1, 2]
    assert GOOD["subject"] in model.calls[1][-1].content  # lần 2 viết dựa trên thư đã gửi lần 1


def test_resume_from_a_new_graph_instance(tmp_path):
    db_file = tmp_path / "flow.db"
    model, outbox = ScriptedChatModel(steps=[letter(**GOOD)]), []
    first = flow(model, outbox, SqliteSaver(sqlite3.connect(db_file, check_same_thread=False)))
    assert pending(start(first, "w6", "KH-0047", "Viết thư nhắc nợ"))  # dừng chờ duyệt, rồi "process" kết thúc

    restarted = flow(
        ScriptedChatModel(steps=[]), outbox, SqliteSaver(sqlite3.connect(db_file, check_same_thread=False))
    )
    final = approve(restarted, "w6")  # như continue_run(run_id=..., session_id=...) của Agno
    assert final["status"] == "sent" and outbox[0]["customer_id"] == "KH-0047"
