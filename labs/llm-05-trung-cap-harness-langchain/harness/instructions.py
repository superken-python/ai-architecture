"""Instructions động — tương đương `instructions=async fn(run_context)` của Agno.

`@dynamic_prompt` chạy trước MỖI lần gọi model và đặt system prompt. Đọc dữ liệu mới (ngữ cảnh UI) mỗi lần.
"""

from __future__ import annotations

from langchain.agents.middleware import ModelRequest, dynamic_prompt

from harness.context import AgentContext

INSTRUCTIONS = """Bạn là trợ lý dữ liệu khách hàng chạy trong Excel.

Luật:
- Tra cứu bằng search_customers trước khi trả lời về một khách hàng. Không bịa mã hay số liệu.
- Trước khi ghi (update_customer, excel_set_values), đọc lại dữ liệu hiện tại.
- Thiếu thông tin để ghi thì hỏi lại một câu ngắn, không đoán.
- Trả lời ngắn, nêu rõ đã thay đổi gì.

Ngữ cảnh giao diện:
{ui}"""


@dynamic_prompt
def instructions(request: ModelRequest) -> str:
    ctx = request.runtime.context
    ui = ctx.describe() if isinstance(ctx, AgentContext) else "(không có)"
    return INSTRUCTIONS.format(ui=ui)
