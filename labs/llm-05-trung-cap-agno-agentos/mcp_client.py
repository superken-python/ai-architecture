import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent


async def collect_metrics() -> tuple[list[dict], list[dict]]:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "mcp_db_server.py")],
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await session.read_resource("schema://enterprise/metrics")
            quarters = []
            for quarter in ("2026-Q2", "2026-Q1"):
                response = await session.call_tool("get_metrics", {"quarter": quarter})
                if response.is_error:  # mcp 2.x: isError (v1) đổi thành is_error
                    raise RuntimeError(str(response.content))
                # Server này trả list[dict]; SDK v1.x có thể trả từng row
                # trong từng TextContent hoặc một JSON array trong một block.
                rows = []
                for block in response.content:
                    if block.type != "text":
                        continue
                    value = json.loads(block.text)
                    rows.extend(value if isinstance(value, list) else [value])
                quarters.append(rows)
            return quarters[0], quarters[1]


if __name__ == "__main__":
    print(asyncio.run(collect_metrics()))
