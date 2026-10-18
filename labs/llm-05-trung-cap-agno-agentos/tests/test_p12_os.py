"""AgentOS chạy như production: tiến trình riêng, có security key, tracing bật, gọi qua HTTP."""

import asyncio

import httpx
import pytest

from agno_lab.p11_workflow import WRITER
from agno_lab.p12_client import demo
from mock_llm import answer_json, call, say
from servers import free_port, process_server
from settings_paths import clean_storage, storage_file

KEY = "khoa-bi-mat-cua-test"
AUTH = {"Authorization": f"Bearer {KEY}"}
ANALYST = "Luôn lấy số liệu bằng get_quarter_kpis"  # câu trong instructions của kpi-analyst (Phần 1)
MEMORY = "You are a Memory Manager"
GOOD = {
    "executive_summary": ["CLOUD_OPS chi phí tăng 18%.", "FIN_TECH doanh thu giảm 12,5%."],
    "actions": ["Rà soát chi phí."],
}


@pytest.fixture(scope="module")
def os_url(_environment, tmp_path_factory):
    """`uvicorn agno_lab.p12_os:create_app --factory` — đúng lệnh bạn chạy, chỉ khác cổng và file db."""
    port = free_port()
    db_file = tmp_path_factory.mktemp("os") / "agno.db"
    args = ["-m", "uvicorn", "agno_lab.p12_os:create_app", "--factory", "--port", str(port)]
    with process_server(args, port, AGNO_DB=str(db_file), OS_SECURITY_KEY=KEY) as url:
        yield url


def test_security_key_guards_every_route_except_health(os_url):
    assert httpx.get(f"{os_url}/health").status_code == 200
    assert httpx.get(f"{os_url}/agents").status_code == 401
    assert httpx.get(f"{os_url}/agents", headers={"Authorization": "Bearer sai"}).status_code == 401
    agents = httpx.get(f"{os_url}/agents", headers=AUTH).json()
    assert [a["id"] for a in agents] == [
        "kpi-analyst",
        "report-writer",
        "report-assistant",
        "memory-assistant",
        "report-operator",
    ]


def test_client_demo_runs_agent_and_workflow_then_reads_traces(os_url, llm, monkeypatch):
    monkeypatch.setenv("OS_SECURITY_KEY", KEY)  # p12_client đọc key từ biến môi trường
    clean_storage("wf-api-wf")
    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), say("CLOUD_OPS và FIN_TECH bị cảnh báo."), match=ANALYST)
    llm.script(answer_json(GOOD), match=WRITER)

    result = asyncio.run(demo(os_url))
    assert result["answer"] == "CLOUD_OPS và FIN_TECH bị cảnh báo."
    assert result["sessions"] == ["api-01"]
    assert result["workflow_paused_at"] == "publish" and result["workflow_status"] == "COMPLETED"
    assert result["traces"] == 1  # một run của agent = một trace, lọc được theo session
    assert storage_file("wf-api-wf", "v1.md").exists()  # bước publish chạy sau khi duyệt qua REST
    clean_storage("wf-api-wf")


def test_trace_tree_has_agent_llm_and_tool_spans(os_url, llm):
    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), say("Có 2 phòng bị cảnh báo."), match=ANALYST)
    form = {"message": "Phòng nào bị cảnh báo 2026-Q2?", "user_id": "an", "session_id": "trace-01", "stream": "false"}
    run = httpx.post(f"{os_url}/agents/kpi-analyst/runs", data=form, headers=AUTH, timeout=60).json()
    assert run["status"] == "COMPLETED"

    (summary,) = httpx.get(f"{os_url}/traces", params={"session_id": "trace-01"}, headers=AUTH).json()["data"]
    assert summary["agent_id"] == "kpi-analyst" and summary["run_id"] == run["run_id"]
    trace = httpx.get(f"{os_url}/traces/{summary['trace_id']}", headers=AUTH).json()
    (root,) = trace["tree"]
    assert root["type"] == "AGENT"
    assert [(s["type"], s["name"]) for s in root["spans"]] == [
        ("LLM", "OpenAIChat.ainvoke"),  # lượt 1: model gọi tool
        ("TOOL", "get_quarter_kpis"),
        ("LLM", "OpenAIChat.ainvoke"),  # lượt 2: model đọc kết quả, trả lời
    ]


def test_memory_written_by_a_rest_run_is_listed_over_rest(os_url, llm):
    llm.script(say("Chào Minh."), match="Cá nhân hoá theo memory")
    llm.script(call("add_memory", memory="Minh phụ trách khối Cloud"), say("ok"), match=MEMORY)
    form = {"message": "Tôi là Minh, phụ trách khối Cloud", "user_id": "minh", "session_id": "m1", "stream": "false"}
    assert httpx.post(f"{os_url}/agents/memory-assistant/runs", data=form, headers=AUTH, timeout=60).status_code == 200

    page = httpx.get(f"{os_url}/memories", params={"user_id": "minh"}, headers=AUTH).json()
    assert [m["memory"] for m in page["data"]] == ["Minh phụ trách khối Cloud"]
    assert page["data"][0]["agent_id"] == "memory-assistant"
