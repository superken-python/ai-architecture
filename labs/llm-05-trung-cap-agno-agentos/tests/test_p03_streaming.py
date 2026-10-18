import asyncio

from agno.run.agent import RunEvent

from agno_lab.p01_agent import build_agent
from agno_lab.p03_streaming import atimeline, timeline
from mock_llm import call, say

ANSWER = "Cloud và FinTech bị cảnh báo, AI Lab đạt."


def test_event_order_with_tool(llm):
    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), say(ANSWER))
    names = [e.event for e in build_agent().run("KPI 2026-Q2?", stream=True, stream_events=True)]
    order = [RunEvent.run_started, RunEvent.tool_call_started, RunEvent.tool_call_completed, RunEvent.run_completed]
    positions = [names.index(e.value) for e in order]
    assert positions == sorted(positions)  # bắt đầu → tool → tool xong → hoàn tất
    assert names.count(RunEvent.run_content.value) >= 2  # chữ đến theo nhiều mảnh
    assert llm.requests[0]["stream"] is True


def test_timeline_text_and_final_output(llm):
    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), say(ANSWER))
    text = "".join(timeline("KPI 2026-Q2?"))
    assert "[tool] get_quarter_kpis({'quarter': '2026-Q2'})" in text
    assert ANSWER in text and "[xong] COMPLETED" in text


def test_without_stream_events_only_content(llm):
    llm.script(say(ANSWER))
    names = {e.event for e in build_agent().run("chào", stream=True)}
    assert RunEvent.run_content.value in names
    assert RunEvent.tool_call_started.value not in names and RunEvent.model_request_started.value not in names


def test_async_stream(llm):
    llm.script(say(ANSWER))

    async def collect():
        return "".join([piece async for piece in atimeline("chào")])

    assert asyncio.run(collect()) == ANSWER
