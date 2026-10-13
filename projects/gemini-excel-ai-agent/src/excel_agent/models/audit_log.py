from datetime import datetime

try:
    from sqlmodel import Field, SQLModel
except ImportError:
    from pydantic import BaseModel, Field  # type: ignore

    class SQLModel(BaseModel):  # type: ignore
        def __init_subclass__(cls, **kwargs):
            kwargs.pop("table", None)
            super().__init_subclass__(**kwargs)


class AuditLog(SQLModel, table=True):
    """
    Bảng ghi vết kiểm toán các thao tác can thiệp dữ liệu Excel (Audit Trail).
    Tuân thủ ORM SQLModel (table=True).
    """

    id: int | None = Field(default=None, description="ID bản ghi")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Thời điểm thao tác")
    session_id: str = Field(description="ID phiên làm việc")
    action_type: str = Field(description="Loại hành động: INSERT_ROW / UPDATE_CELL / SEARCH")
    target_sheet: str = Field(description="Tên worksheet mục tiêu")
    target_row_or_range: str | None = Field(default=None, description="Tọa độ dòng hoặc ô")
    payload_summary: str = Field(description="Tóm tắt dữ liệu đã chèn/sửa")
    executed_by: str = Field(default="user", description="Thực hiện bởi: user / agent")
