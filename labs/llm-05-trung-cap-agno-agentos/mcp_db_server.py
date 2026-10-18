import argparse

from mcp.server.mcpserver import MCPServer  # mcp 2.x: FastMCP (v1) đổi tên thành MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from service import read_metrics

mcp = MCPServer("enterprise-report-lab")


@mcp.resource("schema://enterprise/metrics")
def schema() -> str:
    return (
        "department_metrics(dept_code TEXT, quarter TEXT, revenue_usd INTEGER, "
        "cost_usd INTEGER, active_projects INTEGER); key=(dept_code, quarter). "
        "Money is USD, quarter format YYYY-Q1..Q4."
    )


@mcp.tool()
def get_metrics(quarter: str) -> list[dict]:
    """Đọc metrics của một quý có dạng YYYY-Q1..Q4, không nhận SQL tự do."""
    try:
        return read_metrics(quarter)
    except ValueError as exc:
        # mcp 2.x giấu chi tiết mọi exception lạ ("Error executing tool ..."); lỗi đã lường trước phải là
        # ToolError thì model mới đọc được hướng dẫn sửa.
        raise ToolError(str(exc)) from exc


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", type=int, help="chạy streamable-http ở cổng này thay vì stdio")
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="streamable-http", host="127.0.0.1", port=args.http)
    else:
        mcp.run(transport="stdio")
