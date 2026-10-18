"""Phần 9 — MCP: agent tự chọn tool nằm ở MCP server (một process khác), qua stdio hoặc HTTP.

uv run python -m agno_lab.p09_mcp wrapper "Doanh thu các khối 2026-Q2?"
uv run python -m agno_lab.p09_mcp stdio   "Doanh thu các khối 2026-Q2?"
uv run python mcp_db_server.py --http 8811          # terminal khác
uv run python -m agno_lab.p09_mcp http    "Doanh thu các khối 2026-Q2?"
"""

from __future__ import annotations

import asyncio
import json
import sys

from agno.agent import Agent, RunOutput
from agno.tools.mcp import MCPTools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from agno_lab.settings import ROOT, model

SERVER = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp_db_server.py")])
INSTRUCTIONS = ["Lấy số liệu bằng tool MCP get_metrics; không tự đoán số.", "Trả lời ngắn bằng tiếng Việt."]


# Cách A — tự bọc client MCP trong một function tool (client của Lab 00 §7). Ta kiểm soát hoàn toàn lúc mở/đóng
# kết nối, nhưng phải tự viết schema tool (qua docstring) cho từng tool của server. `is_error` là tên của mcp 2.x.
async def fetch_quarter_metrics(quarter: str) -> str:
    """Đọc số liệu thô (doanh thu, chi phí, số dự án) của mọi phòng ban trong một quý YYYY-Q1..Q4 qua MCP."""
    async with stdio_client(SERVER) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("get_metrics", {"quarter": quarter})
    texts = [block.text for block in result.content if block.type == "text"]
    if result.is_error:
        return f"Lỗi MCP: {' '.join(texts)}"
    rows: list = []
    for text in texts:  # server trả list[dict] thành MỖI dòng một TextContent — gom lại thành một mảng JSON
        value = json.loads(text)
        rows.extend(value if isinstance(value, list) else [value])
    return json.dumps(rows, ensure_ascii=False)


def wrapper_agent() -> Agent:
    return Agent(id="mcp-wrapper", model=model(), tools=[fetch_quarter_metrics], instructions=INSTRUCTIONS)


# Cách B — MCPTools: Agno kết nối server, ĐỌC danh sách tool + schema từ server rồi đưa cho model.
# Server thêm tool mới thì agent thấy ngay, không sửa code agent. Cần mcp>=2.1 với agno 3.1.3.
def stdio_tools() -> MCPTools:
    return MCPTools(server_params=SERVER, include_tools=["get_metrics"], timeout_seconds=30)


def http_tools(url: str = "http://127.0.0.1:8811/mcp") -> MCPTools:
    return MCPTools(url=url, transport="streamable-http", timeout_seconds=30)


async def ask(question: str, tools: MCPTools) -> RunOutput:
    async with tools:  # mở kết nối (stdio: khởi động subprocess server) và đóng khi xong
        agent = Agent(id="mcp-native", model=model(), tools=[tools], instructions=INSTRUCTIONS)
        return await agent.arun(question)


if __name__ == "__main__":
    mode, question = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "Doanh thu các khối 2026-Q2?"
    if mode == "wrapper":
        run = asyncio.run(wrapper_agent().arun(question))
    else:
        run = asyncio.run(ask(question, stdio_tools() if mode == "stdio" else http_tools()))
    print(run.content)
