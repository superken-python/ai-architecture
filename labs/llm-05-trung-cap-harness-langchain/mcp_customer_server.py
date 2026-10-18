"""MCP server nhỏ cho lab: công bố tra cứu khách hàng (dữ liệu của harness/data.py) qua stdio.

Dùng SDK mcp 1.x (FastMCP) vì langchain-mcp-adapters 0.3.2 cần mcp<2. Lab Agno (Agno 3.1.3) thì cần mcp>=2.1:
hai lab chạy ở hai môi trường riêng.

    python mcp_customer_server.py      # thường không chạy tay: client khởi động nó như một subprocess
"""

from __future__ import annotations

from harness.data import CustomerDB
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

mcp = FastMCP("customers")
DB = CustomerDB()


@mcp.tool()
def find_customers(query: str) -> list[dict]:
    """Tìm khách hàng theo mã (KH-0012), một phần tên hoặc thành phố."""
    rows = DB.search(query)
    if not rows:
        raise ToolError(f"Không thấy khách hàng khớp '{query}'. Thử mã dạng KH-0012 hoặc tên thành phố.")
    return rows


if __name__ == "__main__":
    mcp.run(transport="stdio")
