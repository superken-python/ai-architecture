"""MCP client — Agno `MCPTools` ↔ `langchain-mcp-adapters` (`MultiServerMCPClient`).

Đã đo với langchain-mcp-adapters 0.3.2 (cần mcp<2; lab Agno cần mcp>=2.1 → hai lab, hai môi trường):
- `get_tools()` đọc danh sách tool + schema từ server, trả `StructuredTool` CHỈ có bản async → agent phải chạy
  `ainvoke`; `invoke` đồng bộ ném `NotImplementedError: StructuredTool does not support sync invocation`.
- Mặc định mỗi lần gọi tool mở một session MỚI (với stdio là khởi động lại subprocess server). Muốn giữ một
  session cho cả run: `async with client.session(name) as s: tools = await load_mcp_tools(s)`.
- `ToolError` của server tới được model: ToolMessage `status="error"`, nội dung "Error executing tool ...: <lỗi>".
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

LAB = Path(__file__).resolve().parents[1]
SERVERS = {
    "customers": {"command": sys.executable, "args": [str(LAB / "mcp_customer_server.py")], "transport": "stdio"},
}


async def ask_with_mcp(model: BaseChatModel, question: str, *, one_session: bool = True) -> dict[str, Any]:
    client = MultiServerMCPClient(SERVERS)
    system = "Tra cứu khách hàng bằng tool MCP find_customers; không tự đoán số liệu."
    if not one_session:
        agent = create_agent(model, tools=await client.get_tools(), system_prompt=system)
        return await agent.ainvoke({"messages": [{"role": "user", "content": question}]})
    async with client.session("customers") as session:  # một subprocess cho cả run
        agent = create_agent(model, tools=await load_mcp_tools(session), system_prompt=system)
        return await agent.ainvoke({"messages": [{"role": "user", "content": question}]})
