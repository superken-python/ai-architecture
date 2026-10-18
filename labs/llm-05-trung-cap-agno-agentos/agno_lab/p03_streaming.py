"""Phần 3 — Streaming: nhận token và sự kiện (tool, model, hoàn tất) ngay khi chúng xảy ra.

uv run python -m agno_lab.p03_streaming "KPI quý 2026-Q2 thế nào?"
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator, Iterator

from agno.run.agent import RunEvent, RunOutput

from agno_lab.p01_agent import build_agent


def timeline(question: str) -> Iterator[str]:
    """stream=True: nhận dữ liệu theo từng mảnh. stream_events=True: nhận cả sự kiện tool/model, không chỉ chữ."""
    for event in build_agent().run(question, stream=True, stream_events=True, yield_run_output=True):
        if isinstance(event, RunOutput):  # yield_run_output=True: phần tử cuối là RunOutput đầy đủ
            yield f"\n[xong] {event.status.value}, {event.metrics.total_tokens} token"
        elif event.event == RunEvent.run_content.value and event.content:
            yield event.content  # một mảnh token
        elif event.event == RunEvent.tool_call_started.value:
            yield f"\n[tool] {event.tool.tool_name}({event.tool.tool_args})"
        elif event.event == RunEvent.tool_call_completed.value:
            yield f"\n[tool xong] {str(event.tool.result)[:60]}...\n"


async def atimeline(question: str) -> AsyncIterator[str]:
    """Bản async — dùng trong server (FastAPI) để không chặn event loop. Không bật stream_events: chỉ nhận chữ."""
    async for event in build_agent().arun(question, stream=True):
        if event.event == RunEvent.run_content.value and event.content:
            yield event.content


if __name__ == "__main__":
    for piece in timeline(sys.argv[1] if len(sys.argv) > 1 else "KPI quý 2026-Q2 thế nào?"):
        print(piece, end="", flush=True)
    print()
