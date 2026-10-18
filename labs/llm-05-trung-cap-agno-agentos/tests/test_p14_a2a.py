import asyncio
import json

import httpx
import pytest

from agno_lab.p14_a2a import (
    AGENT_ID,
    REMOTE_LEAD,
    RESEARCH,
    ask_research,
    create_research_app,
    research_url,
    team_with_remote_member,
)
from mock_llm import call, say, serve_in_thread


@pytest.fixture
def research():
    """Research service chạy thật (uvicorn trong thread nền), dùng db của test."""
    return serve_in_thread(create_research_app())


def test_agent_card_is_the_public_description_of_the_remote_agent(research):
    card = httpx.get(f"{research_url(research)}/.well-known/agent-card.json").json()
    assert card["name"] == "Market Research"
    assert card["description"].startswith("Tra cứu thông tin thị trường")  # lấy từ Agent.description
    assert card["capabilities"]["streaming"] is True and card["protocolVersion"] == "0.3.0"
    assert card["skills"][0]["id"] == AGENT_ID


def test_raw_json_rpc_message_send(research, llm):
    llm.script(call("lookup_market", topic="cloud"), say("Fixture: chưa có benchmark chi phí cloud."), match=RESEARCH)
    body = {
        "jsonrpc": "2.0",
        "id": "req-1",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": "m-1",
                "role": "user",
                "contextId": "ctx-raw",
                "parts": [{"kind": "text", "text": "Benchmark chi phí cloud?"}],
            }
        },
    }
    task = httpx.post(f"{research_url(research)}/v1/message:send", json=body, timeout=60).json()["result"]
    assert task["kind"] == "task" and task["status"]["state"] == "completed" and task["contextId"] == "ctx-raw"
    (reply,) = task["history"]
    assert reply["role"] == "agent" and reply["parts"] == [
        {"kind": "text", "text": "Fixture: chưa có benchmark chi phí cloud."}
    ]


def test_a2a_client_and_context_id_keep_the_conversation(research, llm):
    llm.script(say("Fixture: chưa có dữ liệu FinTech."), say("Vẫn là FinTech, vẫn fixture."), match=RESEARCH)

    async def conversation():  # cả hội thoại trong MỘT event loop: client A2A của Agno dùng chung kết nối HTTP
        first = await ask_research("Thị trường FinTech?", base=research, context_id="ctx-1")
        await ask_research("Còn quý sau?", base=research, context_id="ctx-1")
        return first

    first = asyncio.run(conversation())
    assert first["agent"] == "Market Research" and first["status"] == "completed"
    assert first["context_id"] == "ctx-1" and first["answer"] == "Fixture: chưa có dữ liệu FinTech."
    second = json.dumps(llm.requests[-1]["messages"], ensure_ascii=False)
    assert "Thị trường FinTech?" in second  # contextId = session_id phía server → có lịch sử tin nhắn trước


def test_team_delegates_to_a_remote_member_over_a2a(research, llm):
    llm.script(
        call("delegate_task_to_member", member_id=AGENT_ID, task="Thị trường FinTech?"),
        say("Tổng hợp: research chưa có benchmark (fixture)."),
        match=REMOTE_LEAD,
    )
    llm.script(call("lookup_market", topic="FinTech"), say("Fixture: chưa có benchmark FinTech."), match=RESEARCH)
    team = team_with_remote_member(research)
    run = asyncio.run(team.arun("So sánh FinTech với thị trường", session_id="a2a-team"))  # .run() không dùng được

    assert run.content == "Tổng hợp: research chưa có benchmark (fixture)."
    assert [(m.agent_id, m.content) for m in run.member_responses] == [
        (AGENT_ID, "Fixture: chưa có benchmark FinTech.")
    ]
    leader_system = llm.requests_for(REMOTE_LEAD)[0]["messages"][0]["content"]
    assert (
        '<member id="market-research"' in leader_system and "Tra cứu thông tin thị trường" in leader_system
    )  # từ card
