from pydantic import BaseModel, Field

from excel_agent.schemas.excel import InsertRowRequest, PreviewDiffCard
from excel_agent.schemas.search import ProductItemDTO


class ChatMessageDTO(BaseModel):
    """Mô hình tin nhắn trong phiên hội thoại."""

    role: str = Field(..., description="Vai trò: user / assistant / system")
    content: str = Field(..., description="Nội dung tin nhắn")


class ChatRequest(BaseModel):
    """Yêu cầu chat gửi từ Excel Taskpane Add-in lên backend AI Agent."""

    message: str = Field(..., description="Nội dung câu chat hoặc lệnh của người dùng")
    session_id: str = Field(default="default-session", description="ID phiên làm việc")
    active_sheet_name: str = Field(default="Sheet1", description="Tên worksheet đang mở")
    table_headers: list[str] = Field(default_factory=list, description="Danh sách tên các cột trên bảng tính")
    row_count: int = Field(default=0, description="Số dòng dữ liệu hiện có trong bảng tính")


class ChatResponse(BaseModel):
    """Phản hồi của AI Agent gửi về cho Excel Taskpane."""

    reply_text: str = Field(..., description="Lời phản hồi văn bản của trợ lý AI")
    session_id: str = Field(..., description="ID phiên làm việc")
    suggested_action: InsertRowRequest | None = Field(default=None, description="Hành động thao tác Excel đề xuất")
    preview_diff: PreviewDiffCard | None = Field(
        default=None, description="Thẻ xem trước thay đổi nếu có hành động can thiệp"
    )
    products_found: list[ProductItemDTO] = Field(default_factory=list, description="Danh sách sản phẩm tìm thấy nếu có")


class SlashCommandRequest(BaseModel):
    """Yêu cầu thực thi lệnh tắt Slash Command (ví dụ: /search <query>)."""

    command_text: str = Field(..., description="Chuỗi lệnh đầy đủ, ví dụ: '/search Áo thun'")
    session_id: str = Field(default="default-session", description="ID phiên làm việc")


class SlashCommandResponse(BaseModel):
    """Kết quả thực thi lệnh tắt Slash Command."""

    command_type: str = Field(..., description="Loại lệnh: search / insert / help")
    raw_query: str = Field(..., description="Từ khóa hoặc tham số bóc tách được")
    reply_text: str = Field(..., description="Thông báo kết quả")
    items: list[ProductItemDTO] = Field(default_factory=list, description="Dữ liệu kết quả nếu là lệnh tìm kiếm")
