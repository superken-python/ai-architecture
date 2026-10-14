from typing import Any

from pydantic import BaseModel, Field


class ColumnMatchDTO(BaseModel):
    """Thông tin một ô tìm thấy trong cột Excel."""

    row_index: int = Field(..., description="Chỉ số dòng (1-indexed)")
    column_letter: str = Field(..., description="Ký hiệu cột, ví dụ: 'A', 'B'")
    cell_address: str = Field(..., description="Tọa độ ô, ví dụ: 'B12'")
    current_value: str = Field(..., description="Giá trị hiện tại của ô")


class SearchColumnRequest(BaseModel):
    """Yêu cầu tìm kiếm giá trị trong một cột của Excel."""

    sheet_name: str | None = Field(default=None, description="Tên worksheet, None là sheet active")
    column_identifier: str = Field(..., description="Tên tiêu đề cột (ví dụ 'Mã sản phẩm') hoặc ký hiệu 'B'")
    search_query: str = Field(..., description="Giá trị cần tìm")
    match_exact: bool = Field(default=True, description="Tìm chính xác hay tìm kiếm tương đối")


class SearchColumnResponse(BaseModel):
    """Kết quả tìm kiếm trong cột Excel."""

    found: bool = Field(..., description="Có tìm thấy hay không")
    matches: list[ColumnMatchDTO] = Field(default_factory=list, description="Danh sách các ô khớp")
    total_scanned_rows: int = Field(default=0, description="Số dòng đã quét")
    header_found: bool = Field(default=True, description="Đã tìm thấy tiêu đề cột hay không")


class ColumnValueDTO(BaseModel):
    """Dữ liệu của một cột khi chèn hoặc cập nhật."""

    column_name: str = Field(..., description="Tên cột theo tiêu đề (ví dụ 'Tên sản phẩm')")
    value: Any = Field(..., description="Giá trị dữ liệu")
    formula: str | None = Field(default=None, description="Công thức Excel nếu có, ví dụ '=C12*D12'")


class InsertRowRequest(BaseModel):
    """Yêu cầu chèn nguyên một dòng dữ liệu vào bảng tính."""

    sheet_name: str | None = Field(default=None, description="Tên worksheet")
    target_row_index: int | None = Field(default=None, description="Vị trí dòng cần chèn, None là cuối bảng")
    row_values: list[ColumnValueDTO] = Field(..., description="Danh sách các giá trị tương ứng từng cột")
    highlight_inserted_row: bool = Field(default=True, description="Có bôi màu dòng vừa chèn không")


class InsertRowResponse(BaseModel):
    """Kết quả chèn dòng dữ liệu."""

    success: bool = Field(..., description="Trạng thái thực thi")
    inserted_at_row: int = Field(..., description="Vị trí dòng thực tế đã chèn")
    cells_updated_count: int = Field(..., description="Số ô đã ghi dữ liệu")
    undo_token: str = Field(..., description="Token dùng để hoàn tác Undo")


class PreviewDiffItem(BaseModel):
    """Một mục thay đổi dữ liệu trong thẻ xem trước Preview Diff."""

    column_name: str = Field(..., description="Tên cột")
    current_value: str | None = Field(default=None, description="Giá trị cũ (nếu có)")
    new_value: str = Field(..., description="Giá trị mới dự kiến ghi vào")
    is_new_row: bool = Field(default=True, description="Là chèn dòng mới hay ghi đè ô cũ")


class PreviewDiffCard(BaseModel):
    """Thẻ giao diện xem trước hành động trước khi thực thi vào Excel (Human-in-the-Loop)."""

    action_type: str = Field(default="INSERT_ROW", description="Loại hành động: INSERT_ROW / UPDATE_CELL")
    sheet_name: str = Field(..., description="Worksheet tác động")
    target_row: int = Field(..., description="Dòng dự kiến tác động")
    summary: str = Field(..., description="Mô tả hành động bằng ngôn ngữ tự nhiên")
    diff_items: list[PreviewDiffItem] = Field(default_factory=list, description="Chi tiết các cột sẽ thay đổi")
    can_apply: bool = Field(default=True, description="Có thể áp dụng ngay không")
