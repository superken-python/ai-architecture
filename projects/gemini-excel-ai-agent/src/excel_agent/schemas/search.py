from pydantic import BaseModel, Field


class ProductItemDTO(BaseModel):
    """Mô hình dữ liệu sản phẩm chuẩn Pydantic v2 trả về cho API và Agent."""

    id: int = Field(..., description="ID sản phẩm")
    sku: str = Field(..., description="Mã SKU sản phẩm")
    name: str = Field(..., description="Tên sản phẩm")
    category: str = Field(..., description="Danh mục sản phẩm")
    unit_price: float = Field(..., description="Đơn giá niêm yết (VNĐ)")
    stock_quantity: int = Field(default=0, description="Số lượng tồn kho")
    unit: str = Field(default="Cái", description="Đơn vị tính")
    status: str = Field(default="Kinh doanh", description="Trạng thái")
    description: str | None = Field(default=None, description="Mô tả chi tiết")


class SearchRequest(BaseModel):
    """Yêu cầu tìm kiếm cơ sở dữ liệu doanh nghiệp."""

    query: str = Field(..., description="Từ khóa tìm kiếm (tên, mã SKU, mô tả)")
    category: str | None = Field(default=None, description="Lọc theo danh mục nếu có")
    min_price: float | None = Field(default=None, description="Giá thấp nhất")
    max_price: float | None = Field(default=None, description="Giá cao nhất")
    limit: int = Field(default=10, description="Số lượng kết quả tối đa")


class SearchResponse(BaseModel):
    """Kết quả tìm kiếm cơ sở dữ liệu."""

    query: str = Field(..., description="Từ khóa đã tìm kiếm")
    total_found: int = Field(..., description="Tổng số mục tìm thấy")
    items: list[ProductItemDTO] = Field(default_factory=list, description="Danh sách sản phẩm")
