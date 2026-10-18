import asyncio
import json
import os
import sys
from pathlib import Path

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIChat
from dotenv import load_dotenv

from mcp_client import collect_metrics
from reporting import Narrative, make_evidence, make_prompt, render_report, save_local_report
from rules import load_rules

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def inspect_rules() -> str:
    """Đọc toàn bộ quy ước KPI từ Excel, giữ nguyên rule_id và threshold."""
    return json.dumps(load_rules(), ensure_ascii=False)


def build_agent(thread_id: str) -> Agent:
    model_id = os.environ["MODEL_ID"]
    (ROOT / "storage").mkdir(exist_ok=True)
    return Agent(
        name="enterprise-report",
        model=OpenAIChat(id=model_id),
        db=SqliteDb(db_file=str(ROOT / "storage/agno_sessions.db")),
        session_id=thread_id,
        add_history_to_context=True,
        num_history_runs=5,
        tools=[inspect_rules],
        output_schema=Narrative,
        instructions=[
            "Viết narrative cho báo cáo bằng tiếng Việt.",
            "Dùng evidence được cấp; gọi inspect_rules nếu cần kiểm tra quy ước.",
            "Không viết lại bảng số liệu; ứng dụng sẽ render bảng.",
            "Không suy diễn benchmark từ research fixture.",
        ],
    )


async def main(thread_id: str, instruction: str):
    if not thread_id or not all(c.isalnum() or c in "-_" for c in thread_id):
        raise ValueError("ID chỉ gồm chữ, số, - hoặc _")
    state_path = ROOT / "storage" / f"agno-{thread_id}.json"
    previous = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    # Để dễ kiểm tra số liệu, baseline luôn lấy lại 2 quý qua MCP mỗi lượt.
    current, prior = await collect_metrics()
    evidence = make_evidence(current, prior)
    prompt = make_prompt(evidence, instruction, previous.get("report", ""))
    response = await build_agent(thread_id).arun(prompt)
    narrative = Narrative.model_validate(response.content)
    revision = previous.get("revision", 0) + 1
    report = render_report(evidence, narrative, revision)
    save_local_report(f"agno-{thread_id}", revision, report)
    state = {"revision": revision, "report": report}
    temporary = state_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    temporary.replace(state_path)
    print(report)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit('Dùng: agno_cli.py report-01 "Yêu cầu báo cáo"')
    asyncio.run(main(sys.argv[1], sys.argv[2]))
