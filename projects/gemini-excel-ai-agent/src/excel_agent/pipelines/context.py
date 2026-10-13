from typing import Any

from pydantic import BaseModel, Field

from excel_agent.schemas.excel import InsertRowRequest, PreviewDiffCard
from excel_agent.schemas.search import ProductItemDTO


class PipelineContext(BaseModel):
    """
    Context lưu giữ trạng thái xuyên suốt các bước trong Pipeline (Step-Context Pattern).
    Tuân thủ Pydantic v2.
    """

    session_id: str = Field(default="default-session", description="ID phiên làm việc")
    raw_input: str = Field(..., description="Đầu vào thô của người dùng")
    active_sheet_name: str = Field(default="Sheet1", description="Worksheet hiện tại")
    table_headers: list[str] = Field(default_factory=list, description="Tiêu đề các cột")
    row_count: int = Field(default=0, description="Số dòng dữ liệu")

    # Trạng thái trung gian được các Step cập nhật
    is_slash_command: bool = Field(default=False, description="Có phải lệnh bắt đầu bằng '/'")
    command_name: str | None = Field(default=None, description="Tên lệnh: search / insert / help")
    command_args: str | None = Field(default=None, description="Tham số đi kèm lệnh")

    search_items: list[ProductItemDTO] = Field(default_factory=list, description="Danh sách sản phẩm tìm được")
    suggested_action: InsertRowRequest | None = Field(default=None, description="Hành động Excel đề xuất")
    preview_diff: PreviewDiffCard | None = Field(default=None, description="Thẻ xem trước hành động")

    final_reply_text: str = Field(default="", description="Câu trả lời cuối cùng cho người dùng")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata bổ sung")
