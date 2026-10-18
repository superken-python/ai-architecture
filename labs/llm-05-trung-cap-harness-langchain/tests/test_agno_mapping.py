"""Phần còn lại của Agno (Lab 01) dựng bằng LangChain: hành vi đã đo của từng bên, chỗ giống và chỗ khác."""

from __future__ import annotations

import asyncio

import pytest
from harness.data import CustomerDB
from harness.guards import BLOCKED_URL, build_guarded_agent
from harness.knowledge import POLICIES, KeywordEmbeddings, index, make_policy_tool
from harness.mcp_tools import SERVERS, ask_with_mcp
from harness.model import ScriptedChatModel, call, say
from harness.run import pending, resume_all
from harness.state import build_state_agent
from harness.structured import CustomerBrief, brief, build_brief_agent
from harness.team import build_team, member_answers
from harness.tools import CLIENT_TOOLS
from langchain.agents import create_agent
from langchain.agents.structured_output import StructuredOutputValidationError
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver

GOOD = {"customer_id": "KH-0047", "summary": "Nợ 79 triệu, sát hạn mức 80 triệu.", "risk": "cao"}


def ask(agent, text: str, thread: str | None = None) -> dict:
    config = {"configurable": {"thread_id": thread}} if thread else None
    return agent.invoke({"messages": [{"role": "user", "content": text}]}, config)


# ---------------------------------------------------------------- Phần 2: output có schema
def test_structured_output_is_a_tool_call_validated_by_pydantic():
    model = ScriptedChatModel(steps=[call("search_customers", query="KH-0047"), call("CustomerBrief", **GOOD)])
    result = brief(build_brief_agent(model, CustomerDB()), "Tóm tắt KH-0047")
    assert isinstance(result, CustomerBrief) and result.risk == "cao"
    assert model.bound_tools[0] == ["search_customers", "CustomerBrief"]  # schema thành một tool


def test_invalid_output_is_sent_back_and_retried_unlike_agno():
    bad = {**GOOD, "customer_id": "0047"}
    model = ScriptedChatModel(steps=[call("CustomerBrief", **bad), call("CustomerBrief", **GOOD)])
    result = brief(build_brief_agent(model, CustomerDB()), "Tóm tắt KH-0047")
    assert result.customer_id == "KH-0047" and len(model.calls) == 2
    error = next(m for m in model.calls[1] if isinstance(m, ToolMessage))
    assert "Failed to parse structured output" in error.content  # model đọc lỗi validate rồi sửa


def test_retry_can_be_turned_off():
    model = ScriptedChatModel(steps=[call("CustomerBrief", **{**GOOD, "risk": "rất cao"})])
    with pytest.raises(StructuredOutputValidationError):
        brief(build_brief_agent(model, CustomerDB(), retry_on_error=False), "Tóm tắt KH-0047")


# ---------------------------------------------------------------- Phần 4: state của session
def test_state_is_updated_by_tool_and_read_by_prompt_across_runs():
    model = ScriptedChatModel(steps=[call("record_revision", note="bản đầu"), say("Đã viết v1."), say("Đang ở v1.")])
    agent = build_state_agent(model, InMemorySaver())
    ask(agent, "Viết thư nhắc nợ KH-0047", thread="s1")
    out = ask(agent, "Đang ở phiên bản nào?", thread="s1")
    assert out["revision"] == 1 and out["notes"] == ["v1: bản đầu"]
    prompts = [call_messages[0].content for call_messages in model.calls]  # system prompt của từng lượt gọi model
    assert "v0" in prompts[0] and "v1" in prompts[1] and "v1" in prompts[2]  # đọc lại state trước MỖI lượt


def test_runtime_parameter_is_hidden_from_the_model():
    from harness.state import record_revision

    assert list(record_revision.tool_call_schema.model_json_schema()["properties"]) == ["note"]


# ---------------------------------------------------------------- Phần 8: guardrail, hook, model dự phòng
def test_pre_hook_blocks_without_calling_the_model():
    model = ScriptedChatModel(steps=[])
    out = ask(build_guarded_agent(model, CustomerDB()), "chào bạn")
    assert out["messages"][-1].content.startswith("Yêu cầu phải nêu mã khách hàng") and model.calls == []


def test_pii_is_redacted_before_the_model_and_in_state():
    model = ScriptedChatModel(steps=[say("Đã ghi nhận.")])
    out = ask(build_guarded_agent(model, CustomerDB()), "KH-0012, gửi về lan@corp.vn")
    assert model.calls[0][-1].content == "KH-0012, gửi về [REDACTED_EMAIL]"
    assert "lan@corp.vn" not in out["messages"][0].content  # khác Agno: state cũng không giữ email


def test_post_hook_replaces_the_bad_answer_unlike_agno():
    model = ScriptedChatModel(steps=[say("Theo https://example.com, ngành tăng 32,5%.")])
    out = ask(build_guarded_agent(model, CustomerDB()), "So sánh KH-0012 với ngành")
    assert out["messages"][-1].content == BLOCKED_URL
    assert not any("example.com" in m.content for m in out["messages"])  # Agno: content vẫn giữ câu vi phạm


class DeadModel(ScriptedChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls.append(list(messages))
        raise ConnectionError("provider không phản hồi")


def test_fallback_model_answers_when_primary_fails():
    primary, backup = DeadModel(steps=[]), ScriptedChatModel(steps=[say("Trả lời từ model dự phòng.")])
    out = ask(build_guarded_agent(primary, CustomerDB(), fallback=backup), "KH-0012 còn nợ bao nhiêu?")
    assert out["messages"][-1].content == "Trả lời từ model dự phòng."
    assert len(primary.calls) == 1 and len(backup.calls) == 1


# ---------------------------------------------------------------- Phần 6: knowledge (RAG)
def test_index_upserts_by_id_and_removes_deleted_documents():
    store = InMemoryVectorStore(KeywordEmbeddings())
    assert index(store, POLICIES) == {"upserted": 3, "removed": 0}
    changed = {k: (v[0].replace("90%", "80%"), v[1]) for k, v in POLICIES.items() if k != "no-qua-han"}
    assert index(store, changed) == {"upserted": 2, "removed": 1}
    assert sorted(store.store) == ["no-90", "thu-nhac-no"] and "80%" in store.store["no-90"]["text"]


def test_agent_searches_policies_with_a_metadata_filter():
    store = InMemoryVectorStore(KeywordEmbeddings())
    index(store, POLICIES)
    model = ScriptedChatModel(steps=[call("search_policies", query="nợ vượt hạn mức tín dụng"), say("Tạm dừng giao.")])
    out = ask(create_agent(model, tools=[make_policy_tool(store)]), "Nợ gần hạn mức thì làm gì?")
    (found,) = [m.content for m in out["messages"] if isinstance(m, ToolMessage)]
    assert found.startswith("[no-90]") and "[thu-nhac-no]" not in found  # style guide bị lọc ra


# ---------------------------------------------------------------- Phần 9: MCP client
def test_mcp_tools_come_from_the_server_and_errors_reach_the_model():
    model = ScriptedChatModel(
        steps=[call("find_customers", query="Hà Nội"), call("find_customers", query="zzz"), say("ok")]
    )
    out = asyncio.run(ask_with_mcp(model, "Khách ở Hà Nội?"))
    assert model.bound_tools[0] == ["find_customers"]  # tên + schema lấy từ server
    found, missing = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    assert "KH-0012" in str(found.content) and "KH-0047" in str(found.content)
    assert missing.status == "error" and "Không thấy khách hàng khớp 'zzz'" in str(missing.content)


def test_mcp_tools_need_async_invocation():
    tools = asyncio.run(MultiServerMCPClient(SERVERS).get_tools())
    model = ScriptedChatModel(steps=[call("find_customers", query="KH-0012"), say("ok")])
    with pytest.raises(NotImplementedError, match="sync invocation"):
        ask(create_agent(model, tools=tools), "KH-0012?")  # invoke đồng bộ


# ---------------------------------------------------------------- Phần 10: team
def test_coordinate_leader_delegates_then_synthesizes():
    lead = ScriptedChatModel(
        steps=[
            call("ask_analyst", task="Công nợ và hạn mức của KH-0047?"),
            call("ask_writer", task="Viết 2 câu nhắc nợ 79.000.000 đồng cho Hải Đăng"),
            say("Đã có số liệu và thư nháp cho KH-0047."),
        ]
    )
    members = {
        "analyst": ScriptedChatModel(steps=[call("search_customers", query="KH-0047"), say("Nợ 79 triệu / 80 triệu.")]),
        "writer": ScriptedChatModel(steps=[say("Kính gửi Hải Đăng, quý khách còn nợ 79.000.000 đồng.")]),
    }
    out = ask(build_team(lead, members.__getitem__, CustomerDB()), "Chuẩn bị nhắc nợ KH-0047")
    assert member_answers(out) == [
        ("ask_analyst", "Nợ 79 triệu / 80 triệu."),
        ("ask_writer", "Kính gửi Hải Đăng, quý khách còn nợ 79.000.000 đồng."),
    ]
    assert out["messages"][-1].content == "Đã có số liệu và thư nháp cho KH-0047." and len(lead.calls) == 3
    member_input = [m.content for m in members["writer"].calls[0] if m.type == "human"]
    assert member_input == ["Viết 2 câu nhắc nợ 79.000.000 đồng cho Hải Đăng"]  # chỉ nhận task, như Agno


def test_route_returns_the_member_answer_verbatim():
    lead = ScriptedChatModel(steps=[call("ask_analyst", task="Hạn mức KH-0012?")])
    members = {
        "analyst": ScriptedChatModel(steps=[say("Hạn mức 300.000.000 đồng.")]),
        "writer": ScriptedChatModel(steps=[]),
    }
    out = ask(build_team(lead, members.__getitem__, CustomerDB(), mode="route"), "Hạn mức của KH-0012?")
    assert out["messages"][-1].content == "Hạn mức 300.000.000 đồng." and len(lead.calls) == 1


# ---------------------------------------------------------------- Phần 7/13: nhiều tool client cùng lượt
def test_two_client_tools_in_one_turn_resume_together():
    both = AIMessage(
        content="",
        tool_calls=[
            {"name": "excel_read_rows", "args": {"rows": [2]}, "id": "c1"},
            {"name": "excel_set_values", "args": {"cells": {"E2": "Hoàn tất"}}, "id": "c2"},
        ],
    )
    model = ScriptedChatModel(steps=[both, say("Đã đọc dòng 2 và ghi E2.")])
    agent = create_agent(model, tools=CLIENT_TOOLS, checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "multi"}}
    out = agent.invoke({"messages": [{"role": "user", "content": "Đọc dòng 2 rồi đánh dấu hoàn tất"}]}, config)
    assert sorted(p["tool_call_id"] for p in pending(out)) == ["c1", "c2"]  # hai interrupt cùng lúc

    half = resume_all(agent, out, {"c1": "Dòng 2: Công ty An Phát"}, thread="multi")
    assert [p["tool_call_id"] for p in pending(half)] == ["c2"] and len(model.calls) == 1  # còn chờ c2

    done = resume_all(agent, half, {"c2": "Đã ghi E2"}, thread="multi")
    assert pending(done) == [] and done["messages"][-1].content == "Đã đọc dòng 2 và ghi E2."
    results = {m.tool_call_id: m.content for m in done["messages"] if isinstance(m, ToolMessage)}
    assert results == {"c1": "Dòng 2: Công ty An Phát", "c2": "Đã ghi E2"}
