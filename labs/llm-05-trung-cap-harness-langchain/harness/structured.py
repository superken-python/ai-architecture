"""Output có schema — Agno `output_schema` ↔ LangChain `create_agent(response_format=...)`.

`ToolStrategy(Schema)`: model trả kết quả bằng cách GỌI một tool mang tên schema; LangChain validate bằng Pydantic.
Khác Agno 3.1.3 (đã đo cả hai):
- Sai schema: Agno chỉ log WARNING, `content` là chuỗi, status vẫn COMPLETED. LangChain (handle_errors=True, mặc định)
  gửi lỗi validate về cho model trong một ToolMessage và cho thử lại; handle_errors=False thì ném
  StructuredOutputValidationError.
- Model trả lời bằng chữ thay vì gọi tool kết quả: LangChain gọi model thêm lượt nữa (và bind tool với
  tool_choice="any" để ép gọi tool).
`ProviderStrategy(Schema)`: dùng structured output gốc của provider (response_format json_schema), không qua tool.
"""

from __future__ import annotations

from typing import Any, Literal

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from harness.data import CustomerDB
from harness.tools import make_server_tools


class CustomerBrief(BaseModel):
    """Tóm tắt một khách hàng cho người phụ trách."""  # docstring thành mô tả của tool kết quả

    customer_id: str = Field(pattern=r"^KH-\d{4}$", description="Mã khách hàng, ví dụ KH-0012")
    summary: str = Field(min_length=10, description="Tình hình công nợ và giao hàng, một hai câu")
    risk: Literal["thấp", "trung bình", "cao"]


def build_brief_agent(model: BaseChatModel, db: CustomerDB, *, retry_on_error: bool = True) -> Any:
    search = make_server_tools(db)[0]  # chỉ cho đọc
    return create_agent(
        model,
        tools=[search],
        system_prompt="Tra cứu khách hàng bằng search_customers rồi trả tóm tắt đúng schema.",
        response_format=ToolStrategy(CustomerBrief, handle_errors=retry_on_error),
        name="brief-agent",
    )


def brief(agent: Any, question: str) -> CustomerBrief:
    """Kết quả đã validate nằm ở `structured_response`, tách khỏi message cuối."""
    return agent.invoke({"messages": [{"role": "user", "content": question}]})["structured_response"]
