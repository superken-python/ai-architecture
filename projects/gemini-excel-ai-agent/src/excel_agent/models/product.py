try:
    from sqlmodel import Field, SQLModel
except ImportError:
    from pydantic import BaseModel, Field  # type: ignore

    class SQLModel(BaseModel):  # type: ignore
        def __init_subclass__(cls, **kwargs):
            kwargs.pop("table", None)
            super().__init_subclass__(**kwargs)


class Product(SQLModel, table=True):
    """
    Bảng dữ liệu danh mục sản phẩm doanh nghiệp giả lập (Mock Enterprise DB).
    Tuân thủ ORM SQLModel (table=True).
    """

    id: int | None = Field(default=None, description="ID sản phẩm")
    sku: str = Field(description="Mã sản phẩm duy nhất")
    name: str = Field(description="Tên sản phẩm")
    category: str = Field(description="Danh mục sản phẩm")
    unit_price: float = Field(description="Đơn giá niêm yết (VNĐ)")
    stock_quantity: int = Field(default=0, description="Số lượng tồn kho")
    unit: str = Field(default="Cái", description="Đơn vị tính")
    status: str = Field(default="Kinh doanh", description="Trạng thái: Kinh doanh / Hết hàng / Ngừng bán")
    description: str | None = Field(default=None, description="Mô tả chi tiết sản phẩm")
